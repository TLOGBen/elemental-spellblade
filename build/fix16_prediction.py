from implement_fix16 import *
c='src/ESSBController.psc'
replace(c,'Function ApplyDamage(Int aiElement, Float afAmount, Actor akTarget)','Function ApplyDamage(Int aiElement, Float afAmount, Actor akTarget, Int aiKillProc = 0)')
replace(c,'\tApplyDamageRaw(aiElement, afAmount * BaseDamageMult.GetValue() * GLevel(ESSBNodes.TreeOf(aiElement)) \\\n\t\t* ESSBElem2.TargetDamageMult(Self, akTarget) \\\n\t\t* ESSBElem3.TargetDamageMult(Self, akTarget), akTarget)', '''\tFloat amount = afAmount * BaseDamageMult.GetValue() * GLevel(ESSBNodes.TreeOf(aiElement)) \\
		* ESSBElem2.TargetDamageMult(Self, akTarget) \\
		* ESSBElem3.TargetDamageMult(Self, akTarget)
	If aiKillProc > 0
		ArmKillProc(akTarget, aiKillProc, afAmount, amount)
	EndIf
	ApplyDamageRaw(aiElement, amount, akTarget)''')
replace(c,'Function ArmKillProc(Actor akTarget, Int aiKind, Float afAmount)','Function ArmKillProc(Actor akTarget, Int aiKind, Float afAmount, Float afPredicted = -1.0)')
replace(c,'\tIf beforeHealth > 0.0 && afAmount >= beforeHealth','\tIf afPredicted < 0.0\n\t\tafPredicted = afAmount\n\tEndIf\n\tIf beforeHealth > 0.0 && afPredicted >= beforeHealth')
replace('src/ESSBElem.psc','\takCtl.ArmKillProc(akTarget, 1, amount)\n\takCtl.ApplyDamage(1, amount, akTarget)','\takCtl.ApplyDamage(1, amount, akTarget, 1)')
replace('src/ESSBStatus.psc','\t\tCtl.ArmKillProc(Holder, 10, amount)\n\t\tCtl.ApplyDamage(10, amount, Holder)','\t\tCtl.ApplyDamage(10, amount, Holder, 10)')
replace('build/fix15_verify.py','GetDamageMult=lambda *a:1.,ApplyDamage=lambda *a:None,SetStack=lambda *a:None','GetDamageMult=lambda *a:1.,ApplyDamage=lambda *a:f.c.ArmKillProc(a[2],a[3],a[1]) if len(a)>3 else None,SetStack=lambda *a:None')
