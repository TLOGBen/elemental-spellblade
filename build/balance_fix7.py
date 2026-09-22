from pathlib import Path
import re, json

sources = {}
endings = {}
def read(p):
    p = str(p)
    if p not in sources:
        b = Path(p).read_bytes()
        endings[p] = '\r\n' if b.count(b'\r\n') == b.count(b'\n') else '\n'
        sources[p] = b.decode('utf-8').replace('\r\n', '\n')
    return sources[p]
def change(file, old, new, fn=None, count=1):
    p = 'src/'+file+'.psc' if not file.endswith(('.py','.json')) else file
    s = read(p)
    start,end = 0,len(s)
    if fn:
        m=re.search(r'^[^\n]*\bFunction '+fn+r'\([^\n]*\n.*?^EndFunction',s,re.M|re.S)
        assert m, (file,fn)
        start,end=m.span()
    block=s[start:end]
    assert block.count(old)==count,(file,fn,old,block.count(old),count)
    sources[p]=s[:start]+block.replace(old,new)+s[end:]

c=change
props='\n'.join('GlobalVariable Property Mult'+n+' Auto' for n in ['Dot','Cooldown','Recovery','Drain','Duration'])
c('ESSBController','GlobalVariable Property NodeScale Auto','GlobalVariable Property NodeScale Auto\n'+props+'\nFloat LastRecoveryScale = -1.0')
helpers='''; fix round 7: category delivery helpers never apply G(L).
Float Function CooldownSeconds(Float afSeconds)
	Return afSeconds * MultCooldown.GetValue()
EndFunction

Float Function DurationSeconds(Float afSeconds)
	If afSeconds <= 0.0
		Return 0.0
	EndIf
	Float seconds = afSeconds * MultDuration.GetValue()
	If seconds < 1.0
		seconds = 1.0
	EndIf
	Return seconds
EndFunction

Int Function DurationInt(Float afSeconds)
	Return (DurationSeconds(afSeconds) + 0.5) as Int
EndFunction

Float Function RecoveryAmount(Float afAmount)
	Return afAmount * MultRecovery.GetValue()
EndFunction

Float Function DrainAmount(Float afAmount)
	Return afAmount * MultDrain.GetValue()
EndFunction

Function ApplyDotDamage(Int aiElement, Float afAmount, Actor akTarget)
	ApplyDamage(aiElement, afAmount * MultDot.GetValue(), akTarget)
EndFunction

'''
c('ESSBController','Function ApplyUtil(Int aiIndex, Float afMagnitude, Int aiDuration, Actor akTarget)',helpers+'Function ApplyUtil(Int aiIndex, Float afMagnitude, Int aiDuration, Actor akTarget, Bool abBalanced = False)')
c('ESSBController','\tutilSpell.SetNthEffectMagnitude(0, afMagnitude)','''	If !abBalanced
		If aiIndex == 4 || aiIndex == 5 || aiIndex == 6 || aiIndex == 18 || aiIndex == 19 || aiIndex == 10 || aiIndex == 11 || aiIndex == 25
			afMagnitude = RecoveryAmount(afMagnitude)
		ElseIf aiIndex == 1 || aiIndex == 2 || aiIndex == 3
			afMagnitude = DrainAmount(afMagnitude)
		ElseIf aiIndex == 7
			afMagnitude = afMagnitude * MultDot.GetValue() * BaseDamageMult.GetValue()
		EndIf
	EndIf
	utilSpell.SetNthEffectMagnitude(0, afMagnitude)''','ApplyUtil')
c('ESSBController','SetNthEffectDuration(0, aiDuration)','SetNthEffectDuration(0, DurationInt(aiDuration))','ApplyUtil')
# Recovery is applied before the existing overflow cap; delivery bypasses only magnitude scaling.
c('ESSBController','Float missing =','afAmount = RecoveryAmount(afAmount)\n\tFloat missing =','Leech')
for old in ['ApplyUtil(4, heal, 0, player)','ApplyUtil(19, overflow, 20, player)','ApplyUtil(4, overflow, 0, player)']:
 c('ESSBController',old,old[:-1]+', True)','Leech')
# Godsave is the explicit 1-HP exception.
c('ESSBGuard','Ctl.ApplyUtil(4, 1.0, 0, player)','Ctl.ApplyUtil(4, 1.0, 0, player, True)')
# Mana break's actual drain and zero-mana test must see the same scaled amount.
c('ESSBNoForm','Float before =','drain = akCtl.DrainAmount(drain)\n\tFloat before =','OnManaBreak')
c('ESSBNoForm','ApplyUtil(2, actual, 0, akTarget)','ApplyUtil(2, actual, 0, akTarget, True)','OnManaBreak')
c('ESSBElem2','GetActorValue("Stamina") <= afStamina','GetActorValue("Stamina") <= akCtl.DrainAmount(afStamina)','QuakeOne')
# All true damage uses the existing damage GLOB once, independently of its G flag.
c('ESSBController','\tElseIf aiTree == 10\n\t\t; Astral Star Sever derives from B_max; noform true damage stays excluded.\n\t\tamount = amount * BaseDamageMult.GetValue()\n\tEndIf','\tEndIf\n\tamount = amount * BaseDamageMult.GetValue()','ApplyTrueDamage')
c('ESSBStatus','Ctl.ApplyDamage(6, bleed * ESSBElem2.BleedPerLayer(Ctl), Holder)','Ctl.ApplyDotDamage(6, bleed * ESSBElem2.BleedPerLayer(Ctl), Holder)')
c('ESSBStatus','Ctl.ApplyDamage(8, venom, Holder)','Ctl.ApplyDotDamage(8, venom, Holder)')
c('ESSBController','ApplyDamage(10, ESSBReactions.ReactDamage(Self, 10, 0.5), victim)','ApplyDotDamage(10, ESSBReactions.ReactDamage(Self, 10, 0.5), victim)','TickDomain')
c('ESSBReactions','remaining * surge +','remaining * akCtl.MultDot.GetValue() * surge +','EndBlood')
# Durations: scale at the final setter (pending state and import paths stay raw).
c('ESSBController','\tIf slot >= 0\n\t\tIf RegElem[slot] == aiElement','\tduration = DurationInt(duration)\n\tIf slot >= 0\n\t\tIf RegElem[slot] == aiElement','ApplyMark')
c('ESSBController','player.DoCombatSpellApply(ManaBreakSpell, akTarget)','ManaBreakSpell.SetNthEffectDuration(0, DurationInt(8))\n\t\tplayer.DoCombatSpellApply(ManaBreakSpell, akTarget)','ApplyManaBreakMark')
c('ESSBController','\tSilenceSpell.SetNthEffectDuration(0, duration)','\tduration = DurationInt(duration)\n\tSilenceSpell.SetNthEffectDuration(0, duration)','ApplySilenceSpell')
c('ESSBController','DomainLeft[slot] = aiSeconds','DomainLeft[slot] = DurationInt(aiSeconds)','StartDomain')
for fn in ['ApplyFear','ApplyFrenzy','ApplyReanimate']:
 c('ESSBController','SetNthEffectDuration(0, aiSeconds)','SetNthEffectDuration(0, DurationInt(aiSeconds))',fn)
c('ESSBController','+ aiSeconds','+ DurationSeconds(aiSeconds)','KeepAsSecond')
c('ESSBController','Utility.GetCurrentRealTime() + 4.0','Utility.GetCurrentRealTime() + DurationSeconds(4.0)','FinishMark')
# Self windows, including zero used to cancel, share the duration helper.
for fn in ['SetMolten','SetEmber','SetQuench','SetShockRecent','SetGuardSwitch','SetGuardBurst','SetGuardIce','SetThunder','SetDoubleBurst','SetSyncKeep','SetOpenBoost','SetEndBoost','SetBloodthirst','SetGuardWind','SetGuardDivine','SetCloakGuard','SetNoBloodCost','SetWindFollow','SetRiposte','KeepSneak','SetGuardDark','SetGuardAstral','SetGuardStar']:
 p='src/ESSBController.psc'; s=read(p); m=re.search(r'^[^\n]*\bFunction '+fn+r'\([^\n]*\n.*?^EndFunction',s,re.M|re.S)
 # Scale once before comparisons as well as assignments, preserve 0 cancellation.
 block=m[0]; first=block.index('\n')
 sources[p]=s[:m.start()]+block[:first+1]+'\taiSeconds = DurationInt(aiSeconds)\n'+block[first+1:]+s[m.end():]
for fn in ['SetAirborne','SetCatalyze','SetDeathCurse','SetStarLock']:
 p='src/ESSBStatus.psc'; s=read(p); m=re.search(r'^[^\n]*\bFunction '+fn+r'\([^\n]*\n.*?^EndFunction',s,re.M|re.S)
 block=m[0]; first=block.index('\n'); sources[p]=s[:m.start()]+block[:first+1]+'\taiSeconds = Ctl.DurationInt(aiSeconds)\n'+block[first+1:]+s[m.end():]
c('ESSBStatus','FreezeSeconds = afSeconds','FreezeSeconds = Ctl.DurationSeconds(afSeconds)','SetFrozen')
c('ESSBStatus','Float frozenSeconds = 3.0 + ESSBElem.FrozenExtraSeconds(Ctl)','Float frozenSeconds = Ctl.DurationSeconds(3.0 + ESSBElem.FrozenExtraSeconds(Ctl))','Tick')
for field,seconds in [('HeatTime','6.0'),('FreezeTime','6.0'),('FissureTime','8.0'),('UnbalanceTime','3.0'),('HolyTime','8.0'),('PressureTime','8.0'),('CurseTime','8.0')]:
 c('ESSBStatus',f'now - {field} >= {seconds}',f'now - {field} >= Ctl.DurationSeconds({seconds})','Tick')
c('ESSBStatus','now - WetTime >= ESSBElem3.WetSeconds(Ctl)','now - WetTime >= Ctl.DurationSeconds(ESSBElem3.WetSeconds(Ctl))','Tick')
c('ESSBController','Utility.GetCurrentRealTime() - TwinTime <= 30.0','Utility.GetCurrentRealTime() - TwinTime <= DurationSeconds(30.0)')
# Cooldowns: do not scale scheduling, FX/log budgets, XP caps, combo deadlines, or status lives.
for field,secs,count in [('RegLastOpen[aiSlot]','1.0',2),('RegLastEnd[aiSlot]','1.0',1),('InterruptTime','5.0',1),('IceHeartTime','30.0',1),('RetaliateTime','10.0',1),('SanctuaryTime','30.0',1),('CleanseTime','3.0',1)]:
 c('ESSBController',f'now - {field} < {secs}',f'now - {field} < CooldownSeconds({secs})',count=count)
c('ESSBController','now - last < window','now - last < CooldownSeconds(window)','TakePush')
c('ESSBGuard','now - RecentTime[index] < 3.0','now - RecentTime[index] < Ctl.CooldownSeconds(3.0)')
c('ESSBController','StormCharge >= 3','StormCharge >= CooldownSeconds(3.0)','Tick')
c('ESSBController','Int avatarCd = ESSBNodes.AvatarCooldown(Self)','Int avatarCd = (CooldownSeconds(ESSBNodes.AvatarCooldown(Self)) + 0.5) as Int','Tick')
c('ESSBStatus','SpreadCounter >= interval','SpreadCounter >= Ctl.CooldownSeconds(interval)','Tick')
c('ESSBTrees','Utility.GetCurrentGameTime() - stamp.GetValue() >= 1.0','Utility.GetCurrentGameTime() - stamp.GetValue() >= Controller.CooldownSeconds(86400.0) / 86400.0','RespecReady')
# Direct inheritance shield and recovery-rate abilities are outside ApplyUtil.
c('ESSBController','akVictim.GetActorValueMax("Health") * 0.1','RecoveryAmount(akVictim.GetActorValueMax("Health") * 0.1)','ApplyInherit')
c('ESSBController','\tplayer.DoCombatSpellApply(InheritSpell, player)','\tInt effect = 0\n\tWhile effect < 7\n\t\tInheritSpell.SetNthEffectDuration(effect, DurationInt(15))\n\t\teffect += 1\n\tEndWhile\n\tplayer.DoCombatSpellApply(InheritSpell, player)','ApplyInherit')
refresh='''Function RefreshRecovery()
	Actor player = ThePlayer()
	If !player || !Trees
		Return
	EndIf
	Float mult = MultRecovery.GetValue()
	Perk ice = Trees.GetBranch(1, 0, 3, 0)
	Perk shock = Trees.GetBranch(2, 0, 3, 0)
	Perk water = Trees.GetBranch(8, 0, 3, 0)
	Perk holy = Trees.GetBranch(6, 0, 1, 1)
	ice.SetNthEntryValue(0, 0, 1.0 - 0.3 * mult)
	shock.SetNthEntryValue(0, 0, 1.0 - 0.15 * mult)
	water.SetNthEntryValue(0, 0, 1.0 - 0.3 * mult)
	Int index = 0
	While index < 5
		holy.SetNthEntryValue(index, 0, 1.0 - 0.1 * mult)
		index += 1
	EndWhile
	player.RemoveSpell(WarmBloodAbility)
	player.RemoveSpell(InductionAbility)
	WarmBloodAbility.SetNthEffectMagnitude(0, RecoveryAmount(20.0))
	InductionAbility.SetNthEffectMagnitude(0, RecoveryAmount(20.0))
	RockArmorShown = -1.0
	SyncRockArmor()
	RefreshAbilities()
	LastRecoveryScale = mult
EndFunction

'''
c('ESSBController','Function RefreshAbilities()',refresh+'Function RefreshAbilities()')
c('ESSBController','\tFloat now = Utility.GetCurrentRealTime()','\tIf MultRecovery && LastRecoveryScale != MultRecovery.GetValue()\n\t\tRefreshRecovery()\n\tEndIf\n\tFloat now = Utility.GetCurrentRealTime()','Tick')

# Five appended globals plus existing ESSB_BaseDamageMult = six categories.
entries=''.join(f"    'ESSB_Mult{name}': (0x{0x5168+i:06X}, 'mult_{name.lower()}'),\n" for i,name in enumerate(['Dot','Cooldown','Recovery','Drain','Duration']))
c('build_v03.py',"    'ESSB_WaterOpenStamina': (0x005167, 'water_open_stamina'),","    'ESSB_WaterOpenStamina': (0x005167, 'water_open_stamina'),\n"+entries.rstrip())
settings=json.loads(read('settings.json'))
for name in ['dot','cooldown','recovery','drain','duration']: settings['mult_'+name]=1.0
sources['settings.json']=json.dumps(settings,ensure_ascii=False,indent=2)+'\n'

for p,s in sources.items(): Path(p).write_bytes(s.replace('\n',endings[p]).encode('utf-8'))
print('category scaling applied')

