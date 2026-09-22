exec(open(__file__.replace('fix15_deadlines.py','implement_fix15.py'),encoding='utf8').read().split('files=')[0])
c=read('src/ESSBController.psc').replace('CleanseSelf()','ApplyCleanse(True)')
names=re.findall(r'(?m)^Int (\w+Left)\s*$',c)
for n in names:
 c=c.replace('Int '+n+'\n','Float '+n+'\n')
 # Every nonzero setter stores deadline. Zero is inactive.
 c=re.sub(r'(?m)^(\s*'+n+r' = )(aiSeconds|avatarCd)$',r'\1Utility.GetCurrentRealTime() + \2',c)
 c=c.replace('If aiSeconds > '+n,'If Utility.GetCurrentRealTime() + aiSeconds > '+n)
 c=c.replace(n+' -= 1','If now >= '+n+'\n\t\t\t'+n+' = 0.0\n\t\tEndIf')
 c=re.sub(r'SetGlobal\((\w+), '+n+r'\)',r'SetGlobal(\1, SecondsLeft('+n+'))',c)
 c=c.replace('Return '+n+'\n','Return SecondsLeft('+n+')\n')
# Gate readers without extra native calls when inactive. Tick retains due values until settled.
a=c.index('Function TickTimers()');b=c.index('Bool Function TimersActive()',a)
tick=c[a:b].replace('\tIf MoltenLeft > 0','\tFloat now = Utility.GetCurrentRealTime()\n\tIf MoltenLeft > 0',1)
c=c[:a]+tick+c[b:]
a=c.index('Function TickTimers()');b=c.index('Bool Function TimersActive()',a)
pre,mid,post=c[:a],c[a:b],c[b:]
for n in names:
 if n=='AvatarLeft':continue
 for part in ['pre','post']:
  s=pre if part=='pre' else post
  s=re.sub(r'\b'+n+r' > 0\b', '('+n+' > 0 && '+n+' > Utility.GetCurrentRealTime())',s)
  if part=='pre':pre=s
  else:post=s
c=pre+mid+post
for n,size in [('OpenBoost',12),('EndBoost',12),('DomainLeft',3)]:
 c=c.replace('Int[] '+n,'Float[] '+n).replace(n+' = new Int[',n+' = new Float[')
 c=c.replace(n+'[aiElement] = aiSeconds',n+'[aiElement] = Utility.GetCurrentRealTime() + aiSeconds')
 c=c.replace('Return '+n+'[aiElement]','Return SecondsLeft('+n+'[aiElement])')
 c=c.replace(n+'[slot] = '+n+'[slot] - 1','If Utility.GetCurrentRealTime() >= '+n+'[slot]\n\t\t\t\t'+n+'[slot] = 0.0\n\t\t\tEndIf')
c=c.replace('DomainLeft[slot] = DurationInt(aiSeconds)','DomainLeft[slot] = Utility.GetCurrentRealTime() + DurationSeconds(aiSeconds)')
# Non-tick domain readers cannot treat an expired domain as active. Tick still settles final effect.
for fn in ['AddDomain','InDomain','PlayerInDomain','ScanDomainTargets']:
 m=re.search(r'(?m)^(?:\w+(?:\[\])? )?Function '+fn+r'\([^\n]*\)[\s\S]*?^EndFunction',c)
 if m:
  s=m[0];s=re.sub(r'DomainLeft\[([^]]+)\] > 0',r'DomainLeft[\1] > Utility.GetCurrentRealTime()',s);c=c[:m.start()]+s+c[m.end():]
c=c.replace('Int StormCharge','Float StormCharge')
c=c.replace('StormCharge += 1\n\t\tIf StormCharge >= CooldownSeconds(3.0)\n\t\t\tStormCharge = 0','If StormCharge <= 0\n\t\t\tStormCharge = now + CooldownSeconds(3.0)\n\t\tEndIf\n\t\tIf now >= StormCharge\n\t\t\tStormCharge = now + CooldownSeconds(3.0)')
# Charge decay catches up by elapsed seconds without repeated native calls.
c=c.replace('Float SelfLastHit','Float ChargeDecayAt\nFloat SelfLastHit')
c=c.replace('\t\tSelfCharge -= 1','\t\tFloat decayStart = SelfLastHit + 9.0\n\t\tIf ChargeDecayAt > decayStart\n\t\t\tdecayStart = ChargeDecayAt\n\t\tEndIf\n\t\tInt decay = (now - decayStart) as Int\n\t\tSelfCharge -= decay\n\t\tChargeDecayAt = decayStart + decay\n\t\tIf SelfCharge < 0\n\t\t\tSelfCharge = 0\n\t\tEndIf',1)
# Load adopts the existing reset-short-combat-state policy, deadlines never retain prior uptime.
a=c.index('Function ResetLoadClock()');i=c.index('\tSelfLastHit = now',a)
reset='\tChargeDecayAt = now\n\tStormCharge = 0.0\n\tSwitchCharge = 0\n'
for n in names:reset+='\t'+n+' = 0.0\n'
reset+='\tInt timerIndex = 0\n\tWhile timerIndex < 12\n\t\tOpenBoost[timerIndex] = 0.0\n\t\tEndBoost[timerIndex] = 0.0\n\t\ttimerIndex += 1\n\tEndWhile\n\ttimerIndex = 0\n\tWhile timerIndex < 3\n\t\tDomainLeft[timerIndex] = 0.0\n\t\ttimerIndex += 1\n\tEndWhile\n'
# InitRegistry occurs before Setup calls ResetLoadClock, but explicit initialisation also protects standalone calls.
reset='\tInitRegistry()\n'+reset
c=c[:i]+reset+c[i:]
c=c.replace('\t\tDeadActor[i] = None','\t\tHitActor[i] = None\n\t\tCastActor[i] = None\n\t\tKillProcActor[i] = None\n\t\tDeadActor[i] = None',1)
# Pending timers preserve the request's original deadline through host binding.
for n,fun,args in [('PendingAir','SetAirborne','air, airDamage'),('PendingCatalyze','SetCatalyze','catalyst, catalystMult'),('PendingCurse','SetDeathCurse','curse, curseBase, curseMult')]:
 c=c.replace('Int[] '+n,'Float[] '+n).replace(n+' = new Int[',n+' = new Float[')
 c=c.replace(n+'[slot] = aiSeconds',n+'[slot] = Utility.GetCurrentRealTime() + DurationSeconds(aiSeconds)')
 var=args.split(',')[0];c=c.replace('Int '+var+' = '+n,'Float '+var+' = '+n)
 c=c.replace('akStatus.'+fun+'('+args+')','akStatus.'+fun+'(0, '+','.join(args.split(',')[1:]).strip()+', '+var+')')
# Float status export expanded to 24, 4 slots per backing array (96 <=128).
c=c.replace('new Float[68]','new Float[96]').replace('While index < 17','While index < 24').replace('* 17 + index','* 24 + index').replace('new Float[17]','new Float[24]')
c+='''
Int Function SecondsLeft(Float afDeadline)
\tIf afDeadline <= 0.0
\t\tReturn 0
\tEndIf
\tFloat remaining = afDeadline - Utility.GetCurrentRealTime()
\tIf remaining <= 0.0
\t\tReturn 0
\tEndIf
\tReturn Math.Ceiling(remaining) as Int
EndFunction
'''
write('src/ESSBController.psc',c)
e=read('src/ESSBElem2.psc').replace('Function TryKillStreak(ESSBController akCtl, Int aiKillingElement) Global','Function TryKillStreak(ESSBController akCtl, Int aiKillingElement, Bool abSneak = False) Global');write('src/ESSBElem2.psc',e)
s=read('src/ESSBStatus.psc');sn=['CatalyzeLeft','DeathCurseLeft','AirLeft','StarLockLeft']
s=s.replace('Int SpreadCounter','Float SpreadCounter\nFloat RingClock\nBool Settling')
for n in sn:
 s=s.replace('Int '+n+'\n','Float '+n+'\n').replace(n+' = aiSeconds',n+' = Utility.GetCurrentRealTime() + aiSeconds')
 s=s.replace('If aiSeconds > '+n,'If Utility.GetCurrentRealTime() + aiSeconds > '+n)
 s=s.replace('Return '+n+'\n','Return Ctl.SecondsLeft('+n+')\n')
 s=re.sub(r'(out\[ESSBState.TailOffset\(\) \+ \d\] = )'+n,r'\g<1>0 ; deadlines exported as floats',s)
 s=s.replace(n+' -= 1','If now >= '+n+'\n\t\t\t'+n+' = 0.0\n\t\tEndIf')
for fn,n,old in [('SetAirborne','AirLeft','Int aiSeconds, Float afDamage'),('SetCatalyze','CatalyzeLeft','Int aiSeconds, Float afMult = 1.0'),('SetDeathCurse','DeathCurseLeft','Int aiSeconds, Float afAmount, Float afMult = 1.0')]:
 s=s.replace('Function '+fn+'('+old+')','Function '+fn+'('+old+', Float afDeadline = 0.0)')
 s=s.replace(n+' = Utility.GetCurrentRealTime() + aiSeconds',n+' = Utility.GetCurrentRealTime() + aiSeconds\n\tIf afDeadline > 0.0\n\t\t'+n+' = afDeadline\n\tEndIf',1)
s=s.replace('Return CatalyzeLeft > 0','Return CatalyzeLeft > Utility.GetCurrentRealTime()').replace('Return StarLockLeft > 0','Return StarLockLeft > Utility.GetCurrentRealTime()')
s=s.replace('out[ESSBState.TailOffset() + 4] = SpreadCounter','out[ESSBState.TailOffset() + 4] = 0')
s=s.replace('new Float[17]','new Float[24]')
extra=['CatalyzeLeft','DeathCurseLeft','AirLeft','StarLockLeft','RingClock','SpreadCounter']
a=s.index('Float[] Function ExportFloats()');b=s.index('\tReturn out',a)
s=s[:b]+''.join(f'\tout[{17+i}] = {n}\n' for i,n in enumerate(extra))+s[b:]
a=s.index('Function ImportState(');b=s.index('\tSyncFrozenFx()',a)
s=s[:b]+'\tIf afFloats && afFloats.Length >= 24\n'+''.join(f'\t\t{n} = afFloats[{17+i}]\n' for i,n in enumerate(extra))+'\tEndIf\n'+s[b:]
# RingClock advances actual seconds. Bounded ring sweep settles layer-seconds before ageing/expiry.
a=s.index('\tInt starDelay',s.index('Function Tick()'));b=s.index('\n\n\t; ---- 單層',a)
s=s[:a]+'''\tIf Settling
\t\tReturn
\tEndIf
\tIf RingClock <= 0.0
\t\tRingClock = now
\tEndIf
\tInt elapsed = (now - RingClock) as Int
\tIf elapsed < 1
\t\tReturn
\tEndIf
\tSettling = True
\tInt starDelay = ESSBElem3.AstralDelay(Ctl)
\tInt bleed = 0
\tInt poison = 0
\tInt astral = 0
\tFloat starWeight = 0.0
\tFloat poisonWork = 0.0
\tBool catalyzed = CatalyzeLeft > RingClock
\tFloat venomMult = CatalyzeMult
\tInt step = 0
\tInt horizon = PoisonRing.Length
\tIf BleedRing.Length > horizon
\t\thorizon = BleedRing.Length
\tEndIf
\tWhile step < elapsed && step < horizon
\t\tInt layers = RingSum(PoisonRing)
\t\tbleed += RingSum(BleedRing)
\t\tpoison += layers
\t\tFloat weight = 1.0
\t\tBool active = CatalyzeLeft > RingClock + step
\t\tIf active
\t\t\tweight = ESSBElem3.CatalyzeRate(Ctl) * venomMult
\t\tEndIf
\t\tpoisonWork += layers * weight * ESSBElem3.PoisonTickMult(Ctl, active)
\t\tRingAge(BleedRing)
\t\tRingAge(PoisonRing)
\t\tIf starDelay <= 1
\t\t\tastral += RingSum(AstralRing)
\t\t\tstarWeight += AstralWeight[0] + AstralWeight[1]
\t\t\tClearStack(11)
\t\tElse
\t\t\tastral += RingAge(AstralRing)
\t\t\tstarWeight += AstralWeight[1]
\t\t\tAstralWeight[1] = AstralWeight[0]
\t\t\tAstralWeight[0] = 0.0
\t\tEndIf
\t\tstep += 1
\tEndWhile
\tRingClock += elapsed
\tIf CatalyzeLeft > 0 && now >= CatalyzeLeft
\t\tCatalyzeLeft = 0.0
\t\tCatalyzeMult = 1.0
\tEndIf
\tBool foresee = RingSum(AstralRing) > 0
'''+s[b:]
# Use integrated work rather than applying the old catalyze multiplier a second time.
a=s.index('\t\tFloat venom =',s.index('Function Tick()'));b=s.index('\t\tCtl.ApplyDotDamage(8',a)
s=s[:a]+'''\t\tFloat venom = ESSBReactions.BaseMax(Ctl, 8) * Ctl.PoisonDotK.GetValue() * poisonWork * Ctl.GetDamageMult(8) * ESSBNodes.OmniMult(Ctl)
'''+s[b:]
s=s.replace('\t\tSpreadCounter += 1\n\t\tIf poison >= ESSBElem3.SpreadThreshold(Ctl) && SpreadCounter >= Ctl.CooldownSeconds(interval)\n\t\t\tSpreadCounter = 0','\t\tIf poison >= ESSBElem3.SpreadThreshold(Ctl) && now >= SpreadCounter\n\t\t\tSpreadCounter = now + Ctl.CooldownSeconds(interval)')
a=s.index('Function Tick()');b=s.index('EndFunction',a);s=s[:b]+'\tSettling = False\n'+s[b:]
# Before new stacks/readers: settle elapsed work once, so a late tick cannot erase newly added layers.
for fn in ['AddStack','SetStack','AddAstral','GetStack']:
 a=s.index('Function '+fn+'(');b=s.index('\tInitRings()',a)+len('\tInitRings()')
 s=s[:b]+'\n\tIf RingClock > 0 && !Settling && Holder && !Holder.IsDead()\n\t\tTick()\n\tElseIf RingClock <= 0\n\t\tRingClock = Utility.GetCurrentRealTime()\n\tEndIf'+s[b:]
# New host starts its clock immediately, migration preserves it; load rebases overdue settlement to next tick.
s=s.replace('\tBound = True','\tRingClock = Utility.GetCurrentRealTime()\n\tBound = True',1)
a=s.index('Function ResetLoadClock()');b=s.index('\tHeatTime = now',a)
s=s[:b]+ '\tRingClock = now\n\tSettling = False\n\tSpreadCounter = now\n'+''.join('\tIf '+n+' > 0\n\t\t'+n+' = now + 1.0\n\tEndIf\n' for n in sn)+s[b:]
write('src/ESSBStatus.psc',s)
b=read('build_v03.py').replace('MGEF_MARK_FLAGS | 0x1000','MGEF_MARK_FLAGS | 0x1000 | 0x00200000')
write('build_v03.py',b)
print('deadline conversion written')
