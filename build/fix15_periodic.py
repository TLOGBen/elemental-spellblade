exec(open(__file__.replace('fix15_periodic.py','implement_fix15.py'),encoding='utf8').read().split('files=')[0])
c=read('src/ESSBController.psc')
c=c.replace('Float MoltenLeft','Float MoltenTickAt\nFloat MoltenLeft',1).replace('Float[] DomainLeft','Float[] DomainTickAt\nFloat[] DomainLeft',1)
c=c.replace('\tIf !DomainLeft','\tIf !DomainTickAt\n\t\tDomainTickAt = new Float[3]\n\tEndIf\n\tIf !DomainLeft',1)
a=c.index('Function SetMolten(');b=c.index('\n',a);c=c[:b]+'\n\tMoltenTickAt = Utility.GetCurrentRealTime()'+c[b:]
a=c.index('\tIf MoltenLeft > 0',c.index('Function TickTimers()'));b=c.index('\tIf EmberLeft > 0',a)
s=c[a:b];s=s.replace('\t\tIf now >= MoltenLeft','\t\tFloat stop = now\n\t\tIf stop > MoltenLeft\n\t\t\tstop = MoltenLeft\n\t\tEndIf\n\t\tInt ticks = (stop - MoltenTickAt) as Int\n\t\tMoltenTickAt += ticks\n\t\tIf now >= MoltenLeft',1).replace('If player','If player && ticks > 0').replace('20.0 * GLevel(0)','20.0 * GLevel(0) * ticks');c=c[:a]+s+c[b:]
c=c.replace('DomainLeft[slot] = Utility.GetCurrentRealTime() + DurationSeconds(aiSeconds)','DomainTickAt[slot] = Utility.GetCurrentRealTime()\n\tDomainLeft[slot] = DomainTickAt[slot] + DurationSeconds(aiSeconds)',1)
a=c.index('Function TickDomain()');b=c.index('EndFunction',a);s=c[a:b]
start=s.index('\t; 5.8「血池」');end=s.index('\tActor[] pool',start);s=s[:start]+s[end:]
s=s.replace('\t\t\tInt element = DomainElem[slot]','''\t\t\tFloat stop = Utility.GetCurrentRealTime()
\t\t\tIf stop > DomainLeft[slot]
\t\t\t\tstop = DomainLeft[slot]
\t\t\tEndIf
\t\t\tInt ticks = (stop - DomainTickAt[slot]) as Int
\t\t\tDomainTickAt[slot] += ticks
\t\t\tInt element = DomainElem[slot]
\t\t\tIf ticks > 0 && InsideDomainSlot(player, slot)
\t\t\t\tIf element == 6
\t\t\t\t\tApplyUtil(4, 20.0 * GLevel(5) * ticks, 0, player)
\t\t\t\tElseIf element == 7
\t\t\t\t\tApplyUtil(4, 25.0 * GLevel(6) * ticks, 0, player)
\t\t\t\t\tApplyUtil(5, 20.0 * GLevel(6) * ticks, 0, player)
\t\t\t\tElseIf element == 9
\t\t\t\t\tApplyUtil(4, 15.0 * GLevel(8) * ticks, 0, player)
\t\t\t\t\tApplyUtil(6, 15.0 * GLevel(8) * ticks, 0, player)
\t\t\t\tEndIf
\t\t\tEndIf''')
s=s.replace('If victim','If victim && ticks > 0').replace('AddStackTo(victim, 7, 1)','AddStackTo(victim, 7, ticks)').replace('ESSBReactions.BaseMax(Self, 10) * 0.2 * GetDamageMult(10)','ESSBReactions.BaseMax(Self, 10) * 0.2 * GetDamageMult(10) * ticks')
c=c[:a]+s+c[b:]
c+='''
Bool Function InsideDomainSlot(Actor akTarget, Int aiSlot)
\tIf !akTarget
\t\tReturn False
\tEndIf
\tFloat dx = akTarget.GetPositionX() - DomainX[aiSlot]
\tFloat dy = akTarget.GetPositionY() - DomainY[aiSlot]
\tFloat dz = akTarget.GetPositionZ() - DomainZ[aiSlot]
\tReturn dx * dx + dy * dy + dz * dz <= DomainR[aiSlot] * DomainR[aiSlot]
EndFunction
'''
a=c.index('Event OnWeaponHit(');b=c.index('\tIf targetActor.IsDead()',a);en=c.index('\n',b);c=c[:en]+'\n\t\tIf CachedDebugLevel >= 3\n\t\t\tLogRejectedHit("invalid-actor", akTarget, akSource, akProjectile, aiHitFlagMask, weaponType)\n\t\tEndIf'+c[en:]
write('src/ESSBController.psc',c)
s=read('src/ESSBStatus.psc').replace('If HeatTime > now || FreezeTime > now','If RingClock > now || HeatTime > now || FreezeTime > now');write('src/ESSBStatus.psc',s)
s=read('build/fix8_verify.py').replace('def strip_fix12_logging(source):','def strip_fix12_logging(source):\n    source = re.sub(r"\\((\\w+Left) > 0 && \\1 > Utility.GetCurrentRealTime\\(\\)\\)", r"\\1 > 0", source)');write('build/fix8_verify.py',s)
# Rebuild schema 5 from its released schema-4 baseline after final member additions.
write('state-schema.lock.json',(R/'.codex/pre-fix15-snapshot/state-schema.lock.json').read_text(encoding='utf8'))
import sys
sys.path[:0]=[str(R),str(R/'build')]
import state_schema
state_schema.preflight()
print('periodic windows integrate elapsed time; schema 5 regenerated from released schema 4')
