from pathlib import Path
import re,json,hashlib
R=Path(__file__).resolve().parents[1]
def read(n): return (R/n).read_text(encoding='utf-8-sig')
def write(n,s):
 p=R/n; raw=p.read_bytes(); bom=raw.startswith(b'\xef\xbb\xbf'); crlf=raw.count(b'\r\n')==raw.count(b'\n')
 p.write_bytes((b'\xef\xbb\xbf' if bom else b'')+s.replace('\r\n','\n').replace('\n','\r\n' if crlf else '\n').encode())
def subfun(s,name,body):
 return re.sub(r'(?im)^((?:\w+(?:\[\])? )?Function '+name+r'\([^\n]*\)\s*(?:Global)?)[^\S\n]*\n[\s\S]*?^EndFunction',lambda m:m[1]+'\n'+body.rstrip()+'\nEndFunction',s,count=1)
files=['build_v03.py','settings.json','state-schema.lock.json','實作紀錄.md']+[str(p.relative_to(R)) for p in (R/'src').glob('*.psc')]
(R/'build/fix15-before.json').write_text(json.dumps({n:dict(length=len((b:=(R/n).read_bytes())),sha256=hashlib.sha256(b).hexdigest(),bom=b.startswith(b'\xef\xbb\xbf'),crlf=b.count(b'\r\n'),lf=b.count(b'\n')) for n in files},indent=2),encoding='utf8')
c=read('src/ESSBController.psc')
members='''
; FIX15: target-owned facts and once-only death payloads.
Actor[] HitActor
Bool[] HitSneak
Bool[] HitPower
Int[] HitWeapon
Bool[] HitKillDone
Int HitNext
Int[] DeadCurse
Int[] DeadHeat
Int[] DeadHoly
Int SwitchCharge
Bool DivineArmed
Actor[] CastActor
Float[] CastAt
Int CastNext
Actor[] KillProcActor
Int[] KillProcKind
Float[] KillProcUntil
Float[] KillProcAmount
Int KillProcNext
'''
c=c.replace('; 自身資源（離開形態清空）',members+'\n; 自身資源（離開形態清空）')
init=''
for name,typ in [('HitActor','Actor'),('HitSneak','Bool'),('HitPower','Bool'),('HitWeapon','Int'),('HitKillDone','Bool'),('DeadCurse','Int'),('DeadHeat','Int'),('DeadHoly','Int'),('CastActor','Actor'),('CastAt','Float'),('KillProcActor','Actor'),('KillProcKind','Int'),('KillProcUntil','Float'),('KillProcAmount','Float')]:
 init+=f'\tIf !{name}\n\t\t{name} = new {typ}[8]\n\tEndIf\n'
c=c.replace('\tIf !DeadActor\n',init+'\tIf !DeadActor\n',1)
# Hit facts survive dead-target early return. No additional calls on ordinary live hit.
c=c.replace(' || targetActor.IsDead() || caster.IsDead()', ' || caster.IsDead()',1)
start=c.index('\tBool sneak = Math.LogicalAnd',c.index('Event OnWeaponHit'))
end=c.index('\t; 5.2 關閉傳奇',start)
facts=c[start:end]
c=c[:start]+facts+'''\tInt fact = 0
\tWhile fact < 8 && HitActor[fact] != targetActor
\t\tfact += 1
\tEndWhile
\tIf fact >= 8
\t\tfact = HitNext
\t\tHitNext = (HitNext + 1) % 8
\t\tHitKillDone[fact] = False
\tEndIf
\tHitActor[fact] = targetActor
\tHitSneak[fact] = sneak
\tHitPower[fact] = power
\tHitWeapon[fact] = weaponType
\tIf targetActor.IsDead()
\t\t; Engine weapon damage already killed it: never send corpse damage/open marks.
\t\tIf sneak && FormActive.GetValueInt() == 1 && CurrentElement.GetValueInt() == 5
\t\t\tSetSelf(3, ESSBElem2.WindThreshold(Self))
\t\t\tTakeKillStreak()
\t\tEndIf
\t\tInt deadSlot = FindSlot(targetActor)
\t\tIf deadSlot >= 0
\t\t\tCaptureDeath(deadSlot)
\t\tEndIf
\t\t; Kill callback may have arrived before the weapon callback.
\t\tInt settled = 0
\t\tWhile settled < 8
\t\t\tIf SettledDead[settled] == targetActor
\t\t\t\tSettleSneakKill(targetActor, KillElementFor(targetActor, deadSlot))
\t\t\t\tReturn
\t\t\tEndIf
\t\t\tsettled += 1
\t\tEndWhile
\t\tReturn
\tEndIf
'''+c[end:]
c=c.replace('Function OnNoFormHit(Actor akTarget, Weapon akWeapon, Bool abPower)\n','''Function OnNoFormHit(Actor akTarget, Weapon akWeapon, Bool abPower)
\t; Capture before any spell/native damage can end the casting animation.
\tBool hitCasting = ESSBNoForm.IsCasting(akTarget) || RecentCast(akTarget)
\tFloat riposte = 1.0
\tIf RiposteLeft > 0 && Utility.GetCurrentRealTime() < RiposteLeft
\t\triposte = 1.3
\tEndIf
\tRiposteLeft = 0
''')
c=c.replace('ApplyNoFormBaseline(akTarget, abPower)','ApplyNoFormBaseline(akTarget, abPower, riposte)')
c=c.replace('ESSBNoForm.OnMartialHit(Self, akTarget, akWeapon, abPower)','ESSBNoForm.OnMartialHit(Self, akTarget, akWeapon, abPower, riposte)')
c=c.replace('ESSBNoForm.OnManaBreak(Self, akTarget, abPower)','ESSBNoForm.OnManaBreak(Self, akTarget, abPower, hitCasting)')
c=c.replace('Function ApplyNoFormBaseline(Actor akTarget, Bool abPower)','Function ApplyNoFormBaseline(Actor akTarget, Bool abPower, Float afRiposte = 1.0)').replace('Float amount = NoformBaseTrue','Float amount = NoformBaseTrue * afRiposte')
c=c.replace('Function OnFormSwitched(Int aiOldIndex, Int aiNewIndex)\n\tClearSelfAll()','Function OnFormSwitched(Int aiOldIndex, Int aiNewIndex)\n\tIf aiOldIndex == 3\n\t\tSwitchCharge = SelfCharge\n\tEndIf\n\tClearSelfAll()')
c=c.replace('\t\tPendingDischarge = 0\n\t\tESSBElem.Discharge(Self, akTarget, GetSelf(1), False, 0.5)','\t\tInt charge = PendingDischarge\n\t\tPendingDischarge = 0\n\t\tESSBElem.Discharge(Self, akTarget, charge, False, 0.5)')
c=c.replace('\t\tRegStatus[slot] = None\n\tEndIf\nEndFunction\n\nESSBStatus Function GetStatus','\t\tIf akTarget.IsDead()\n\t\t\tCaptureDeath(slot)\n\t\tEndIf\n\t\tRegStatus[slot] = None\n\tEndIf\nEndFunction\n\nESSBStatus Function GetStatus',1)
c=c.replace('\tInt poison = GetStack(victim, 7)','\tInt poison = GetStack(victim, 7)\n\tInt curse = GetStack(victim, 10)\n\tInt heat = GetStack(victim, 1)\n\tInt holy = GetStack(victim, 6)',1)
c=c.replace('\tDeadPoison[DeadNext] = poison','\tDeadPoison[DeadNext] = poison\n\tDeadCurse[DeadNext] = curse\n\tDeadHeat[DeadNext] = heat\n\tDeadHoly[DeadNext] = holy',1)
c=c.replace('\tDeadNext = (DeadNext + 1) % 8\nEndFunction','\tDeadNext = (DeadNext + 1) % 8\n\tSettleDeadCurse(aiSlot)\nEndFunction',1)
c=c.replace('\t; Claim before calling any other script:', '\tInt captureSlot = FindSlot(akVictim)\n\tIf captureSlot >= 0\n\t\tCaptureDeath(captureSlot)\n\tEndIf\n\t; Claim before calling any other script:',1)
c=c.replace('\tInt poison = 0\n\tIf slot >= 0','\tInt poison = 0\n\tInt curse = 0\n\tIf slot >= 0',1).replace('\t\tpoison = GetStack(akVictim, 7)','\t\tpoison = GetStack(akVictim, 7)\n\t\tcurse = GetStack(akVictim, 10)',1).replace('\t\t\tpoison = DeadPoison[index]','\t\t\tpoison = DeadPoison[index]\n\t\t\tcurse = DeadCurse[index]',1)
c=c.replace('ESSBElem3.OnKill(Self, element, akVictim, poison, killingElement, ash)','ESSBElem3.OnKill(Self, element, akVictim, poison, killingElement, ash, curse)\n\tSettleSneakKill(akVictim, killingElement)\n\tSettleKillProc(akVictim)')
c=c.replace('\tActor target = akSource as Actor\n\tIf !CounterEligible(target)','\tActor target = akSource as Actor\n\tRememberCast(target)\n\tIf !CounterEligible(target)',1)
c+='''
Int Function TakeSwitchCharge()
\tInt value = SwitchCharge
\tSwitchCharge = 0
\tReturn value
EndFunction

Function SettleDeadCurse(Int aiSlot)
\tIf RegStatus[aiSlot]
\t\tRegStatus[aiSlot].ResolveDeathCurse(True)
\tEndIf
\tIf PendingCurse[aiSlot] > 0
\t\tFloat amount = PendingCurseBase[aiSlot] * PendingCurseMult[aiSlot]
\t\tPendingCurse[aiSlot] = 0
\t\tESSBElem3.AfterDeathCurse(Self, RegActor[aiSlot], amount)
\t\tIf CachedDebugLevel >= 1
\t\t\tLogEvent(1, "deathcurse", "settled pending on death")
\t\tEndIf
\tEndIf
EndFunction

Function SettleSneakKill(Actor akVictim, Int aiElement)
\tInt i = 0
\tWhile i < 8
\t\tIf HitActor[i] == akVictim && !HitKillDone[i]
\t\t\tHitKillDone[i] = True
\t\t\tESSBElem2.TryKillStreak(Self, aiElement, HitSneak[i])
\t\t\tReturn
\t\tEndIf
\t\ti += 1
\tEndWhile
EndFunction

Function RememberCast(Actor akTarget)
\tIf !akTarget
\t\tReturn
\tEndIf
\tInt i = 0
\tWhile i < 8 && CastActor[i] != akTarget
\t\ti += 1
\tEndWhile
\tIf i == 8
\t\ti = CastNext
\t\tCastNext = (CastNext + 1) % 8
\tEndIf
\tCastActor[i] = akTarget
\tCastAt[i] = Utility.GetCurrentRealTime()
EndFunction

Bool Function RecentCast(Actor akTarget)
\tInt i = 0
\tFloat now = Utility.GetCurrentRealTime()
\tWhile i < 8
\t\tIf CastActor[i] == akTarget
\t\t\tReturn now >= CastAt[i] && now - CastAt[i] <= 1.5
\t\tEndIf
\t\ti += 1
\tEndWhile
\tReturn False
EndFunction

Function ArmKillProc(Actor akTarget, Int aiKind, Float afAmount)
\tIf !akTarget || akTarget.IsDead()
\t\tReturn
\tEndIf
\tInt i = KillProcNext
\tKillProcNext = (KillProcNext + 1) % 8
\tKillProcActor[i] = akTarget
\tKillProcKind[i] = aiKind
\tKillProcAmount[i] = afAmount
\tKillProcUntil[i] = Utility.GetCurrentRealTime() + ESSBState.KillAttributionSeconds()
EndFunction

Function SettleKillProc(Actor akTarget)
\tInt i = 0
\tFloat now = Utility.GetCurrentRealTime()
\tWhile i < 8
\t\tIf KillProcActor[i] == akTarget
\t\t\tInt kind = KillProcKind[i]
\t\t\tFloat amount = KillProcAmount[i]
\t\t\tFloat due = KillProcUntil[i]
\t\t\tKillProcActor[i] = None
\t\t\tIf due >= now
\t\t\t\tIf kind == 1
\t\t\t\t\tESSBElem.OnCremation(Self, akTarget, amount)
\t\t\t\tElseIf kind == 10
\t\t\t\t\tESSBElem3.OnDeathSoul(Self, akTarget)
\t\t\t\tEndIf
\t\t\tEndIf
\t\tEndIf
\t\ti += 1
\tEndWhile
EndFunction

; Native deferred kill holds the death transition BEFORE lethal damage, including DOT.
; It is paired only when owned by this instance. Existing tick/OnHit service the latch.
Function RefreshDivineProtection()
\tActor player = ThePlayer()
\tIf !player
\t\tReturn
\tEndIf
\tIf DivineArmed && player.GetActorValue("Health") <= 0.0
\t\tDivineSaveUsed = True
\t\t; Restore exactly one actual health point, bypass recovery multipliers.
\t\tplayer.RestoreActorValue("Health", 1.0 - player.GetActorValue("Health"))
\t\tCleanseSelf()
\t\tSetGuardDivine(2)
\t\tDivineArmed = False
\t\tplayer.EndDeferredKill()
\t\tReturn
\tEndIf
\tBool eligible = Enabled.GetValueInt() == 1 && FormActive.GetValueInt() == 1 && !DivineSaveUsed && SyncStage() >= 3 && ESSBNodes.Br(Self, 6, 0, 4, 0)
\tIf eligible && !DivineArmed
\t\tplayer.StartDeferredKill()
\t\tDivineArmed = True
\tElseIf !eligible && DivineArmed
\t\tDivineArmed = False
\t\tplayer.EndDeferredKill()
\tEndIf
EndFunction
'''
# Hook cold state changes; sync update only when divine branch eligible to keep representative cost.
idx=c.index('Function RefreshAbilities('); en=c.index('EndFunction',idx)
c=c[:en]+'\tRefreshDivineProtection()\n'+c[en:]
c=c.replace('\tTickTimers()','\tRefreshDivineProtection()\n\tTickTimers()',1)
# AddSync runs every hit; arm only stage 3, costs nothing for representative sync=0.
idx=c.index('Function AddSync('); en=c.index('EndFunction',idx)
c=c[:en]+'\tIf CachedSync >= CachedT3 && !DivineArmed && !DivineSaveUsed\n\t\tRefreshDivineProtection()\n\tEndIf\n'+c[en:]
write('src/ESSBController.psc',c)
n=read('src/ESSBNoForm.psc').replace('Weapon akWeapon, Bool abPower) Global','Weapon akWeapon, Bool abPower, Float afRiposte = 1.0) Global',1).replace('Float base = WeaponBase(akCtl, akWeapon)','Float base = WeaponBase(akCtl, akWeapon) * afRiposte',1).replace('Actor akTarget, Bool abPower) Global','Actor akTarget, Bool abPower, Bool abHitCasting = False) Global',1).replace('&& IsCasting(akTarget)','&& abHitCasting')
write('src/ESSBNoForm.psc',n)
e=read('src/ESSBElem2.psc');e=e.replace('\tTryKillStreak(akCtl, aiKillingElement)','\t; FIX15: controller dispatches streak with victim-owned attack facts.')
e=e.replace('Function TryKillStreak(ESSBController akCtl, Int aiElement) Global','Function TryKillStreak(ESSBController akCtl, Int aiElement, Bool abSneak = False) Global').replace('!akCtl.LastHitWasSneak()','!abSneak')
write('src/ESSBElem2.psc',e)
e=read('src/ESSBElem3.psc').replace('Bool abAsh = False) Global','Bool abAsh = False, Int aiCurse = 0) Global',1).replace('Int curse = akCtl.GetStack(akTarget, 10)','Int curse = aiCurse')
e=e.replace('If ESSBNodes.Br(akCtl, 9, 2, 3, 0) &&','If !akTarget.IsDead() && ESSBNodes.Br(akCtl, 9, 2, 3, 0) &&',1)
a=e.index('\t; 5.12 關閉專精分支「亡魂」',e.index('Function AfterDeathCurse')); b=e.index('\nEndFunction',a)
block=e[a:b].replace(' && akTarget.GetActorValue("Health") <= 0.0','')
e=e[:a]+e[b:]+ '\nFunction OnDeathSoul(ESSBController akCtl, Actor akTarget) Global\n'+block+'\nEndFunction\n'
write('src/ESSBElem3.psc',e)
e=read('src/ESSBElem.psc');a=e.index('\t; 5.3 關閉大師分支「火葬」',e.index('Function Detonate'));b=e.index('\tIf akCtl.CachedDebugLevel',a)
block=e[a:b].replace(' && akTarget.GetActorValue("Health") <= 0.0','').replace('amount * 0.5','afAmount * 0.5')
e=e[:a]+e[b:];a=e.index('\takCtl.ApplyDamage(1, amount, akTarget)',e.index('Function Detonate'));e=e[:a]+'\takCtl.ArmKillProc(akTarget, 1, amount)\n'+e[a:]
e+='\nFunction OnCremation(ESSBController akCtl, Actor akTarget, Float afAmount) Global\n'+block+'EndFunction\n'
e=e.replace('akCtl.SetPendingDischarge(1)','akCtl.SetPendingDischarge(aiCharge)')
e=e.replace('Function OverloadMult(ESSBController akCtl, Int aiElement) Global','Function OverloadMult(ESSBController akCtl, Int aiElement, Int aiCharge = -1) Global\n\tIf aiCharge < 0\n\t\taiCharge = akCtl.GetSelf(1)\n\tEndIf').replace('&& akCtl.GetSelf(1) >= 8','&& aiCharge >= 8')
write('src/ESSBElem.psc',e)
r=read('src/ESSBReactions.psc');a=r.index('\tInt snapshot = -1');b=r.index('\t; Consume only pending',a); block=r[a:b].replace('snapshot = akCtl.GetSelf(1)','snapshot = akCtl.GetSelf(1)\n\t\tIf aiReason == 0\n\t\t\tsnapshot = akCtl.TakeSwitchCharge()\n\t\tEndIf');r=r[:a]+r[b:];a=r.index('\tIf !abChain',r.index('Function End('));r=r[:a]+block+r[a:]
r=r.replace('ESSBElem.OverloadMult(akCtl, aiElement)','ESSBElem.OverloadMult(akCtl, aiElement, snapshot)').replace('EndFire(akCtl, akTarget, st, mult)','EndFire(akCtl, akTarget, st, mult, aiReason)').replace('Function EndFire(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult) Global','Function EndFire(ESSBController akCtl, Actor akTarget, ESSBStatus akStatus, Float afMult, Int aiReason = 2) Global').replace('ESSBElem.Detonate(akCtl, akTarget, afMult, True)','ESSBElem.Detonate(akCtl, akTarget, afMult, !(aiReason == 1 && ESSBElem.KeepHeatOnBurst(akCtl)))',1)
r=r.replace('If aiElement == 3\n\t\t\takCtl.ConsumeEndCharge(snapshot)','If aiElement == 3 && aiReason != 0\n\t\t\takCtl.ConsumeEndCharge(snapshot)').replace('If aiElement == 3\n\t\takCtl.ConsumeEndCharge(snapshot)','If aiElement == 3 && aiReason != 0\n\t\takCtl.ConsumeEndCharge(snapshot)')
write('src/ESSBReactions.psc',r)
g=read('src/ESSBGuard.psc');a=g.index('\t; 5.9 傳奇分支');b=g.index('\n\t; 5.1 純武藝',a);g=g[:a]+'\tCtl.RefreshDivineProtection()\n'+g[b:];write('src/ESSBGuard.psc',g)
s=read('src/ESSBStatus.psc');a=s.index('\t; ---- 死咒：',s.index('Function Tick()'));b=s.index('\n\tIf Ctl.CachedDebugLevel >= 3',a)
s=s[:a]+'''\tIf DeathCurseLeft > 0 && now >= DeathCurseLeft
\t\tResolveDeathCurse(False)
\tEndIf
'''+s[b:]
s+='''
Function ResolveDeathCurse(Bool abDead = False)
\tIf DeathCurseLeft <= 0
\t\tReturn
\tEndIf
\tFloat amount = DeathCurseAmount * DeathCurseMult
\tFloat mult = DeathCurseMult
\tDeathCurseLeft = 0
\tDeathCurseAmount = 0.0
\tIf !abDead && !Holder.IsDead()
\t\tFloat lost = Holder.GetActorValueMax("Health") - Holder.GetActorValue("Health")
\t\tIf lost > 0.0
\t\t\tamount += lost * ESSBElem3.DeathCurseLostRatio(Ctl) * Ctl.GetDamageMult(10) * mult
\t\tEndIf
\t\tCtl.ArmKillProc(Holder, 10, amount)
\t\tCtl.ApplyDamage(10, amount, Holder)
\tEndIf
\tESSBElem3.AfterDeathCurse(Ctl, Holder, amount)
\tIf Ctl.CachedDebugLevel >= 1
\t\tCtl.LogEvent(1, "deathcurse", "settled dead=" + abDead + " amount=" + amount)
\tEndIf
EndFunction
'''
s=s.replace('\t\t; 死亡就不再排程，等宿主 MGEF 自然結束。','\t\tCtl.CaptureStatusDeath(Holder)\n\t\t; No more DOT scheduling on a corpse.')
write('src/ESSBStatus.psc',s)
c=read('src/ESSBController.psc')+'\nFunction CaptureStatusDeath(Actor akTarget)\n\tInt slot = FindSlot(akTarget)\n\tIf slot >= 0\n\t\tCaptureDeath(slot)\n\tEndIf\nEndFunction\n';write('src/ESSBController.psc',c)
b=read('build_v03.py');b=b.replace("mgef_data(MGEF_MARKER_FLAGS, 1, casting=1, delivery=1)","mgef_data(MGEF_MARKER_FLAGS | 0x00200000, 1, casting=1, delivery=1)")
# Mark flags are declared separately: only target status/mark effects require death persistence.
write('build_v03.py',b)
cfg=read('settings.json').replace('"state_schema_version": 4','"state_schema_version": 5');write('settings.json',cfg)
print('FIX15 mechanics pass written; deadline conversion follows')
