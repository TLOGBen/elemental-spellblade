from pathlib import Path
import re
R=Path('.')
def read(p):return (R/p).read_text(encoding='utf-8-sig')
def write(p,s):
 p=R/p; raw=p.read_bytes() if p.exists() else b'\r\n'; bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''; nl='\r\n' if b'\r\n' in raw else '\n';p.write_bytes(bom+s.replace('\r\n','\n').replace('\n',nl).encode())
def body(s,name):return re.search(r'(?m)^(?:\w+ )?(?:Function|Event) '+name+r'\([^\n]*\)[^\n]*\n[\s\S]*?^End(?:Function|Event)',s).group()
def replace(s,name,new):return s.replace(body(s,name),new.strip())
def tail(s,name,code):
 old=body(s,name);return s.replace(old,old.rsplit('\nEnd',1)[0]+'\n'+code+'\nEnd'+old.rsplit('\nEnd',1)[1])
c=read('src/ESSBController.psc')
props='''; Round 18: player-only proc cache and immutable-layout node mirrors.
Perk Property HitProcPerk Auto
Spell[] Property ProcVariants Auto
Int[] Property ProcElements Auto
Float[] Property ProcRatios Auto
Int[] Property ProcPowers Auto
Int[] Property ProcSneaks Auto
Int[] Property ProcBloodBands Auto
Spell[] Property HitBonusSpells Auto
GlobalVariable Property GDivineArmed Auto
GlobalVariable Property FormNotify Auto
GlobalVariable Property FormSound Auto
ESSBGuard Property Guard Auto
ESSBInput Property InputLayer Auto
Int[] Property RankCacheA Auto
Int[] Property RankCacheB Auto
Int[] Property BranchCacheA Auto
Int[] Property BranchCacheB Auto
Int[] Property LevelMirror Auto
Bool Property NodeMirrorReady Auto
Float[] ProcWritten
Float[] DrainWritten
Bool ProcCacheReady
Int CachedSyncStage
Bool SyncCacheReady
Int AppliedElement
'''
c=c.replace('Perk Property BaseRulesPerk Auto',props+'\nPerk Property BaseRulesPerk Auto')
# Mirror lookups stay on this controller; no Trees instance lock on hit.
c=replace(c,'Rank','''Int Function Rank(Int aiTree, Int aiRoute, Int aiTier)
	If StateBroken || !NodeMirrorReady || aiTree < 0 || aiTree > 12 || aiRoute < 0 || aiRoute > 2 || aiTier < 0 || aiTier > 4
		Return 0
	EndIf
	If aiTree == 11 && aiRoute < 2 && FormActive.GetValueInt() == 1
		Return 0
	EndIf
	Int i = aiTree * 15 + aiRoute * 5 + aiTier
	If i < 120
		Return RankCacheA[i]
	EndIf
	Return RankCacheB[i - 120]
EndFunction''')
c=replace(c,'Br','''Bool Function Br(Int aiTree, Int aiRoute, Int aiTier, Int aiIndex)
	If StateBroken || !NodeMirrorReady || aiTree < 0 || aiTree > 12 || aiRoute < 0 || aiRoute > 2 || aiTier < 0 || aiTier > 4 || aiIndex < 0 || aiIndex > 3
		Return False
	EndIf
	If aiTree == 11 && aiRoute < 2 && FormActive.GetValueInt() == 1
		Return False
	EndIf
	Int i = aiTree * 15 + aiRoute * 5 + aiTier
	Int bits = 0
	If i < 120
		bits = BranchCacheA[i]
	Else
		bits = BranchCacheB[i - 120]
	EndIf
	Int divisor = 1
	If aiIndex == 1
		divisor = 2
	ElseIf aiIndex == 2
		divisor = 4
	ElseIf aiIndex == 3
		divisor = 8
	EndIf
	Return (bits / divisor) % 2 == 1
EndFunction''')
c=replace(c,'GLevel','''Float Function GLevel(Int aiTree)
	If StateBroken || !NodeMirrorReady || aiTree < 0 || aiTree > 12
		Return 1.0
	EndIf
	Return 1.0 + 0.05 * LevelMirror[aiTree]
EndFunction''')
old=body(c,'SyncStage');c=c.replace(old,old.replace('SyncStage()', 'ComputeSyncStage()'))
c+='''
Int Function SyncStage()
	If !SyncCacheReady
		Return ComputeSyncStage()
	EndIf
	Return CachedSyncStage
EndFunction

Function RefreshSyncStage()
	CachedSyncStage = ComputeSyncStage()
	SyncCacheReady = True
EndFunction
'''
c=c.replace('\tInt stage = SyncStage()\n\tIf stage > SyncStageShown','\tRefreshSyncStage()\n\tInt stage = SyncStage()\n\tIf stage > SyncStageShown',1)
c=c.replace('\tIf CachedSync >= CachedT3 && !DivineArmed && !DivineSaveUsed && ESSBNodes.Br(Self, 6, 0, 4, 0)\n\t\tRefreshDivineProtection()\n\tEndIf','')
c=body(c,'PushSyncStage') and c # retain function
c=c.replace('Function PushSyncStage()\n','Function PushSyncStage()\n\tRefreshSyncStage()\n')
# Pure player part: preserve all existing additive grouping, water/wind omissions included.
c+='''
Float Function PlayerElementMult(Int aiElement)
	Int tree = aiElement - 1
	Float mult = 1.0
	If aiElement != 9
		mult += ESSBNodes.Pct(Self, Rank(tree, 0, 1), 0.01)
		mult += ESSBNodes.Pct(Self, Rank(tree, 0, 3), 0.01) * SyncStage()
	EndIf
	If aiElement != 5 && GetOpenBoost(aiElement) > 0
		mult += ESSBNodes.Pct(Self, Rank(tree, 1, 1), 0.01)
	EndIf
	If aiElement == 1
		If SelfOverheat > 0
			If Br(0, 0, 4, 1)
				mult += 0.8
			Else
				mult += 0.5
			EndIf
		EndIf
		If GetMoltenLeft() > 0
			mult += 1.0
		EndIf
	EndIf
	Return mult
EndFunction

Float Function PlayerProcBase(Int aiElement, Bool abPower)
	Float b = (ElementDamageMin[aiElement - 1] + ElementDamageMax[aiElement - 1]) * 0.5
	If aiElement == 3
		b = 13.0
	EndIf
	If abPower
		b *= 1.5
	EndIf
	Float common = 1.0
	If BloodthirstLeft > Utility.GetCurrentRealTime()
		common *= 1.2
	EndIf
	If (aiElement == 7 && EnvNight.GetValueInt() == 0) || (aiElement == 10 && EnvNight.GetValueInt() == 1)
		common *= 1.2
	EndIf
	If EndBoostLeft > Utility.GetCurrentRealTime()
		common *= 1.0 + EndBoostAmount
	EndIf
	Return b * BaseDamageMult.GetValue() * GLevel(aiElement - 1) * common * ESSBNodes.CommonHitMult(Self, aiElement, abPower) * PlayerElementMult(aiElement)
EndFunction

Float Function BloodBandMult(Int aiBand)
	Int band = aiBand
	If Br(5, 0, 2, 0)
		band = 3 - band
	EndIf
	If band == 0
		Return 1.25
	ElseIf band == 1
		Return 1.1
	ElseIf band == 2
		Return 0.85
	EndIf
	Return 0.6
EndFunction

Function RefreshProcMagnitudes()
	If StateBroken || !NodeMirrorReady || !ProcVariants
		Return
	EndIf
	If !ProcCacheReady
		ProcWritten = new Float[64]
		DrainWritten = new Float[64]
		If !ProcWritten || !DrainWritten
			BreakState()
			Return
		EndIf
		Int j = 0
		While j < 64
			ProcWritten[j] = -1.0
			DrainWritten[j] = -1.0
			j += 1
		EndWhile
		ProcCacheReady = True
	EndIf
	Int i = 0
	While i < ProcVariants.Length
		Int e = ProcElements[i]
		Float value = PlayerProcBase(e, ProcPowers[i] == 1) * ProcRatios[i]
		If ProcSneaks[i] == 1
			value *= ESSBElem2.SneakMult(Self)
		EndIf
		If e == 6
			value *= BloodBandMult(ProcBloodBands[i])
		EndIf
		If value != ProcWritten[i]
			ProcVariants[i].SetNthEffectMagnitude(0, value)
			ProcWritten[i] = value
		EndIf
		If e == 3
			Float drain = DrainAmount(value * 0.5)
			If drain != DrainWritten[i]
				ProcVariants[i].SetNthEffectMagnitude(1, drain)
				DrainWritten[i] = drain
			EndIf
		EndIf
		i += 1
	EndWhile
EndFunction

Bool Function TargetProcPossible(Int aiElement, Bool abPower, Bool abSneak, Bool abOpening)
	; Innate heat and holy vulnerability exist even with zero purchased nodes.
	If aiElement == 1 || aiElement == 7
		Return True
	EndIf
	If Br(4, 0, 4, 0) || Br(4, 2, 4, 0) || Rank(9, 0, 2) > 0 || Br(10, 1, 3, 0) || Br(10, 2, 4, 0)
		Return True
	EndIf
	If abOpening && (Br(12, 1, 3, 0) || Br(aiElement - 1, 1, 1, 0))
		Return True
	EndIf
	If aiElement == 2
		Return Rank(1, 0, 2) > 0
	ElseIf aiElement == 3
		Return Br(2, 1, 3, 2)
	ElseIf aiElement == 5
		Return abSneak && Br(4, 2, 4, 1)
	ElseIf aiElement == 9
		Return Br(8, 0, 1, 0)
	ElseIf aiElement == 10
		Return Br(9, 0, 3, 0)
	ElseIf aiElement == 11
		Return abPower && Br(10, 0, 2, 0)
	EndIf
	Return False
EndFunction

Function ApplyBakedProc(Actor akTarget, Int aiElement, Bool abPower, Bool abSneak)
	If !akTarget || akTarget.IsDead() || !ProcCacheReady
		Return
	EndIf
	Int wantedBand = 0
	If aiElement == 6
		wantedBand = BloodBand(ThePlayer().GetActorValuePercentage("Health"))
	EndIf
	Int i = 0
	While i < ProcVariants.Length
		If ProcElements[i] == aiElement && ProcPowers[i] == (abPower as Int) && ProcBloodBands[i] == wantedBand
			If aiElement != 5 || ProcSneaks[i] == (abSneak as Int)
				ApplyTrackedDamage(ThePlayer(), ProcVariants[i], akTarget, aiElement)
				Return
			EndIf
		EndIf
		i += 1
	EndWhile
EndFunction

Int Function BloodBand(Float percent)
	If percent >= 0.85
		Return 0
	ElseIf percent >= 0.5
		Return 1
	ElseIf percent >= 0.2
		Return 2
	EndIf
	Return 3
EndFunction
'''
c=replace(c,'ApplyProc','''Function ApplyProc(Actor akTarget, Int aiElement, Bool abPower, Bool abSneak, Bool abOpening, Int aiSlot = -1, Int aiGeneration = -1)
	If !TargetProcPossible(aiElement, abPower, abSneak, abOpening)
		Return
	EndIf
	If !akTarget || akTarget.IsDead() || aiElement < 1 || aiElement > 11
		Return
	EndIf
	Float b = (ElementDamageMin[aiElement - 1] + ElementDamageMax[aiElement - 1]) * 0.5
	If aiElement == 3
		b = 13.0
	EndIf
	If abPower
		b *= 1.5
	EndIf
	Float full = b * BaseDamageMult.GetValue() * GLevel(aiElement - 1) * GetHitMult(aiElement, akTarget, abPower)
	Float base = PlayerProcBase(aiElement, abPower)
	If aiElement == 6
		base *= GetBloodHitMult()
	EndIf
	If aiElement == 5 && abSneak
		Float sneakMult = ESSBElem2.SneakMult(Self)
		base *= sneakMult
		full *= sneakMult * ESSBElem2.KillStreakMult(Self)
	EndIf
	If abOpening
		full *= ESSBNodes.OpenStrikeMult(Self) * ESSBElem.OpenStrikeMult(Self, aiElement)
	EndIf
	Float bonus = full - base
	If bonus <= 0.0
		Return
	EndIf
	Spell procSpell = HitBonusSpells[aiElement - 1]
	procSpell.SetNthEffectMagnitude(0, bonus)
	If aiElement == 3
		procSpell.SetNthEffectMagnitude(1, DrainAmount(bonus * 0.5))
	EndIf
	ApplyTrackedDamage(ThePlayer(), procSpell, akTarget, aiElement, aiSlot, aiGeneration)
EndFunction''')
# phase-1 approved curve change, old leech/drain remain exact.
c=replace(c,'BloodHitCurve','''Float Function BloodHitCurve(Float percent)
	If percent >= 0.85
		Return 1.25
	ElseIf percent >= 0.5
		Return 1.1
	ElseIf percent >= 0.2
		Return 0.85
	EndIf
	Return 0.6
EndFunction''')
# controller base must use raw bands reversed (not percent inversion).
c=c.replace('Return BloodHitCurve(percent) * extra','Return BloodBandMult(BloodBand(raw)) * extra')
# Bloodrage remains target-independent but HP-dependent; requires engine magnitude modifier below.
c=c.replace('base *= GetBloodHitMult()','base *= GetBloodHitMult()')
old='\tActor caster = ThePlayer()\n\tInt weaponType = ResolveHitWeaponType(caster, akSource, akProjectile)\n'
c=c.replace(old,'',1).replace('LogRejectedHit("disabled", akTarget, akSource, akProjectile, aiHitFlagMask, weaponType)','LogRejectedHit("disabled", akTarget, akSource, akProjectile, aiHitFlagMask)')
c=c.replace('\t; RE::HitData：',old+'\t; RE::HitData：',1)
c=c.replace('\tApplyProc(targetActor, element, power, sneak, opening, hitSlot, hitGeneration)','\tNoteDamageElement(targetActor, element)\n\tIf element != hitElement\n\t\tApplyBakedProc(targetActor, element, power, sneak)\n\tElse\n\t\tApplyProc(targetActor, element, power, sneak, opening, hitSlot, hitGeneration)\n\tEndIf',1)
c=c.replace('ApplyProc(targetActor, element, power, sneak, False)','ApplyBakedProc(targetActor, element, power, sneak)')
# Existing hit facts keep PO3 flag semantics; proc difference uses same native state as perk.
c=c.replace('\tNoteDamageElement(targetActor, element)','\tBool procSneak = caster.IsSneaking()\n\tBool procPower = caster.IsPowerAttacking()\n\tIf ranged\n\t\tprocPower = procSneak\n\tEndIf\n\tNoteDamageElement(targetActor, element)',1)
c=c.replace('ApplyProc(targetActor, element, power, sneak, opening','ApplyProc(targetActor, element, procPower, procSneak, opening')
# refresh points with no target changes
for n in ['RefreshTrees','RefreshAbilities','RefreshRuntimeValues','OnSyncStage','SetMolten','SetOpenBoost','SetEndBoost','SetBloodthirst','ClearSelfAll','OnFormSwitched']:
 c=tail(c,n,'\tRefreshSyncStage()\n\tRefreshProcMagnitudes()')
c=tail(c,'OnSyncStage','\tRefreshDivineProtection()')
for n in ['AddSelf','ClearSelf']:
 c=tail(c,n,'\tIf aiKind == 4 && before != SelfOverheat\n\t\tRefreshProcMagnitudes()\n\tEndIf')
c=c.replace('\tEnvNight.SetValueInt(night)','\tEnvNight.SetValueInt(night)')
c=tail(c,'EnvCheck','\tIf changed\n\t\tRefreshProcMagnitudes()\n\tEndIf')
# TickTimers already owns expiration; no new polling loop.
c=tail(c,'TickTimers','\tRefreshSyncStage()\n\tRefreshProcMagnitudes()')
c=c.replace('\tPlayFormSound(FxSoundDrawSheathe, aiOldIndex)','\t; Round 18: switching has only the new form activation cue.')
c=c.replace('\tPlayFormSound(FxSoundFormActive, aiIndex)','\tIf FormSound && FormSound.GetValueInt() == 1\n\t\tPlayFormSound(FxSoundFormActive, aiIndex)\n\tEndIf')
c=c.replace('\t\tDivineArmed = False','\t\tDivineArmed = False\n\t\tSetGlobal(GDivineArmed, 0)')
c=c.replace('\t\tDivineArmed = True','\t\tDivineArmed = True\n\t\tSetGlobal(GDivineArmed, 1)')
c=c.replace('\n\tDivineArmed = False','\n\tDivineArmed = False\n\tSetGlobal(GDivineArmed, 0)')
c+='''
Function OnLethalHitWhileArmed()
	If IsOperational() && DivineArmed
		RefreshDivineProtection()
	EndIf
EndFunction
'''
c=c.replace('\tIf BaseRulesPerk && !player.HasPerk(BaseRulesPerk)','\tIf HitProcPerk && !player.HasPerk(HitProcPerk)\n\t\tplayer.AddPerk(HitProcPerk)\n\tEndIf\n\tIf BaseRulesPerk && !player.HasPerk(BaseRulesPerk)')
c=c.replace('\tReady = True\n\tPO3_Events_Alias.RegisterForWeaponHit(Self)','\tAppliedElement = CurrentElement.GetValueInt()\n\tRefreshSyncStage()\n\tRefreshProcMagnitudes()\n\tReady = True\n\tIf InputLayer\n\t\tInputLayer.Setup()\n\tEndIf\n\tPO3_Events_Alias.RegisterForWeaponHit(Self)')
# Input owns desired globals. AppliedElement is the last settled form.
c=replace(c,'ToggleForm','''Function ToggleForm(Int aiIndex)
	If IsOperational() && InputLayer
		InputLayer.RequestSwitch(aiIndex)
	EndIf
EndFunction''')
sw=body(c,'SwitchForm');sw=sw.replace('\tActor player = ThePlayer()','\taiIndex = CurrentElement.GetValueInt()\n\tIf FormActive.GetValueInt() != 1\n\t\tCloseForm()\n\t\tReturn\n\tEndIf\n\tActor player = ThePlayer()',1)
sw=sw.replace('\tInt previous = 0\n\tIf FormActive.GetValueInt() == 1\n\t\tprevious = CurrentElement.GetValueInt()\n\tEndIf','\tInt previous = AppliedElement\n\tAppliedElement = aiIndex')
sw=sw.replace('\tCurrentElement.SetValueInt(aiIndex)\n\tFormActive.SetValueInt(1)\n','')
sw=sw.replace('\tScheduleTick(1.0)','\tRefreshProcMagnitudes()\n\tScheduleTick(1.0)')
c=replace(c,'SwitchForm',sw)
cl=body(c,'CloseForm').replace('\tInt previous = CurrentElement.GetValueInt()','\tInt previous = AppliedElement\n\tIf previous == 0\n\t\tprevious = CurrentElement.GetValueInt()\n\tEndIf\n\tAppliedElement = 0');c=replace(c,'CloseForm',cl)
write('src/ESSBController.psc',c)
n=read('src/ESSBNodes.psc')
n=replace(n,'Rank','''Int Function Rank(ESSBController akCtl, Int aiTree, Int aiRoute, Int aiTier) Global
	If !akCtl
		Return 0
	EndIf
	Return akCtl.Rank(aiTree, aiRoute, aiTier)
EndFunction''')
n=replace(n,'Br','''Bool Function Br(ESSBController akCtl, Int aiTree, Int aiRoute, Int aiTier, Int aiIndex) Global
	If !akCtl
		Return False
	EndIf
	Return akCtl.Br(aiTree, aiRoute, aiTier, aiIndex)
EndFunction''')
n=replace(n,'GL','''Float Function GL(ESSBController akCtl, Int aiTree) Global
	If !akCtl
		Return 1.0
	EndIf
	Return akCtl.GLevel(aiTree)
EndFunction''')
write('src/ESSBNodes.psc',n)
t=read('src/ESSBTrees.psc')
code='''	Controller.RankCacheA = AllRankA
	Controller.RankCacheB = AllRankB
	Controller.BranchCacheA = AllBranchA
	Controller.BranchCacheB = AllBranchB
	Controller.LevelMirror = LevelCache
	Controller.NodeMirrorReady = True'''
t=tail(t,'RefreshTree',code)
t=tail(t,'RefreshActive','\tController.RefreshSyncStage()\n\tController.RefreshProcMagnitudes()\n\tIf Controller.Guard\n\t\tController.Guard.RefreshNodeBits()\n\tEndIf\n\tIf Controller.InputLayer\n\t\tController.InputLayer.RefreshPermission()\n\tEndIf')
write('src/ESSBTrees.psc',t)
