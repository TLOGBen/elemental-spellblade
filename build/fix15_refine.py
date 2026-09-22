exec(open(__file__.replace('fix15_refine.py','implement_fix15.py'),encoding='utf8').read().split('files=')[0])
c=read('src/ESSBController.psc')
c=c.replace('\tIf !KillStreakReady\n','\tIf !KillStreakReady || KeepSneakLeft <= Utility.GetCurrentRealTime()\n',1)
# Stop mark expiry from scheduling a new curse on an already dead actor.
a=c.index('Function OnMarkFinish(');b=c.index('EndFunction',a);s=c[a:b].replace('CaptureDeath(slot)\n\t\tEndIf','CaptureDeath(slot)\n\t\t\tReturn\n\t\tEndIf');c=c[:a]+s+c[b:]
a=c.index('Function ClearSlot(');i=c.index('\tClearPendingState(aiSlot)',a);c=c[:i]+'\tIf RegActor[aiSlot] && RegActor[aiSlot].IsDead()\n\t\tCaptureDeath(aiSlot)\n\tEndIf\n'+c[i:]
# Guard first-hit capture for live hit callbacks, and suppress stale facts after resurrection.
c=c.replace('\tEndIf\n\t; 5.2 關閉傳奇分支「雙生」', '\tEndIf\n\tHitKillDone[fact] = False\n\t; 5.2 關閉傳奇分支「雙生」',1)
c=c.replace('\t\t\tTakeKillStreak()\n','\t\t\tTakeKillStreak()\n\t\t\tESSBElem2.LethalAmbush(Self, targetActor)\n',1)
# Pending curse cannot be lost when it is queued after the death snapshot.
a=c.index('Function SetDeathCurseOn(');b=c.index('\n',a)
c=c[:b]+'''\n\tIf akTarget && akTarget.IsDead()
\t\tESSBElem3.AfterDeathCurse(Self, akTarget, afBase * afMult)
\t\tReturn
\tEndIf'''+c[b:]
# One proc reason per victim: next successful cause replaces the previous one.
c=c.replace('\tInt i = KillProcNext\n\tKillProcNext = (KillProcNext + 1) % 8','\tInt i = 0\n\tWhile i < 8 && KillProcActor[i] != akTarget\n\t\ti += 1\n\tEndWhile\n\tIf i == 8\n\t\ti = KillProcNext\n\t\tKillProcNext = (KillProcNext + 1) % 8\n\tEndIf')
# Freeze causal window when death is first captured; delayed dispatch doesn't erase valid evidence.
c=c.replace('\tSettleDeadCurse(aiSlot)\nEndFunction','\tInt proc = 0\n\tFloat deathAt = Utility.GetCurrentRealTime()\n\tWhile proc < 8\n\t\tIf KillProcActor[proc] == victim && KillProcUntil[proc] >= deathAt\n\t\t\tKillProcUntil[proc] = -1.0\n\t\tEndIf\n\t\tproc += 1\n\tEndWhile\n\tSettleDeadCurse(aiSlot)\nEndFunction',1).replace('If due >= now','If due == -1.0 || due >= now')
# Rebase all pending deadlines and reset expired native mirrors on load.
a=c.index('Function ResetLoadClock()');b=c.index('\t\tHitActor[i] = None',a)
c=c[:b]+''.join('\t\tIf '+n+'[i] > 0\n\t\t\t'+n+'[i] = now + 1.0\n\t\tEndIf\n' for n in ['PendingAir','PendingCurse','PendingCatalyze'])+c[b:]
# Ensure owned native death latch is released on fail-closed shutdown as well.
a=c.index('Function BreakState()');b=c.index('\n',a);c=c[:b]+'\n\tIf DivineArmed && PlayerRef\n\t\tDivineArmed = False\n\t\tPlayerRef.EndDeferredKill()\n\tEndIf'+c[b:]
write('src/ESSBController.psc',c)
e=read('src/ESSBElem2.psc')+'''
; Terminal physical sneak attack: the victim is already dead, but the ambush's
; nearby-target effect remains meaningful. Never open marks or damage the corpse.
Function LethalAmbush(ESSBController akCtl, Actor akTarget) Global
\tIf !ESSBNodes.Br(akCtl, 4, 1, 2, 1)
\t\tReturn
\tEndIf
\tActor[] nearby = akCtl.ScanTargets(akTarget, 210.0, 2, akTarget)
\tInt i = 0
\tWhile i < nearby.Length
\t\tIf nearby[i]
\t\t\tWindBlade(akCtl, nearby[i], 1.0)
\t\t\tBlowAway(akCtl, nearby[i], 1.0)
\t\tEndIf
\t\ti += 1
\tEndWhile
EndFunction
''';write('src/ESSBElem2.psc',e)
s=read('build/fix6_verify.py').replace('env=dict(defaults);','env=dict(Utility=NS(GetCurrentRealTime=lambda:0.0));env.update(defaults);');write('build/fix6_verify.py',s)
# Standalone verifier runner avoids recompiling while iterating fixtures.
(R/'build/fix15_existing.py').write_text("import runpy,sys\nfrom pathlib import Path\nsys.dont_write_bytecode=True\nr=Path(__file__).resolve().parents[1]\nsys.path[:0]=[str(r),str(r/'build')]\nfor n in range(6,15):\n print('CHECK',n,flush=True)\n runpy.run_path(str(r/f'build/fix{n}_verify.py'))['run']()\n",encoding='utf8')
print('death/expiry and terminal sneak refinements written')
