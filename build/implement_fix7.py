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

# Amounts and G are deliberately at producers; ApplyUtil adds no tree scaling.
c=change
c('ESSBReactions','BaseMax(akCtl, 6) * akCtl.GetBloodLeechRatio()', '50.0 * akCtl.GLevel(5) * akCtl.GetBloodLeechRatio()', 'Open') #01
c('ESSBElem2','ESSBReactions.BaseMax(akCtl, 6) * akCtl.GetBloodLeechRatio()', 'ESSBReactions.BaseMax(akCtl, 6) * 5.0 * akCtl.GLevel(5) * akCtl.GetBloodLeechRatio()', 'OnBloodHit')
c('ESSBController','SetGuardSwitch(1)','SetGuardSwitch(2)','SwitchForm')
c('ESSBElem2','ESSBReactions.BaseMax(akCtl, 7) * 0.02 * heal','1.0 * heal * akCtl.GLevel(6)','OnDivineHit')
c('ESSBElem2','6, 3.0,','6, 15.0 * akCtl.GLevel(4),','WindBladeOne')
c('ESSBNoForm','* 0.5 * aiMarks','* 2.0 * aiMarks * akCtl.GLevel(11)','OnBurst')
c('ESSBElem3','heal + ESSBReactions.BaseMax(akCtl, 8) * 0.5','heal + 6.0 * akCtl.GLevel(7)','PoisonFormTick')
c('ESSBElem3','ESSBReactions.BaseMax(akCtl, 8) * 0.5','25.0 * akCtl.GLevel(7)','OpenPoison')
c('ESSBElem2','Float drain = 0.5 * ESSBNodes.Rank(akCtl, 3, 0, 2)','Float drain = 3.0 * ESSBNodes.Rank(akCtl, 3, 0, 2) * akCtl.GLevel(3)','OnEarthHit') #11,20
c('ESSBElem2','ESSBReactions.BaseMax(akCtl, 6) * 0.5','25.0 * akCtl.GLevel(5)','OpenBlood')
c('ESSBReactions','ReactDamage(akCtl, 7, 0.5) * mult','25.0 * akCtl.GetDamageMult(7) * akCtl.GLevel(6) * mult','Open')
c('ESSBController','ApplyUtil(6, 5.0,','ApplyUtil(6, 20.0 * GLevel(0),','TickTimers')
c('ESSBElem','3, 5.0,','3, 25.0 * akCtl.GLevel(1),','OnFrozenTick')
c('ESSBElem2','6, 5.0,','6, 25.0 * akCtl.GLevel(4),','OnWindHit')
c('ESSBController','ESSBReactions.BaseMax(Self, 9)','15.0 * GLevel(8)','TickDomain',2)
c('ESSBElem2','ESSBReactions.BaseMax(akCtl, 7) * 0.05 * rank','2.0 * rank * akCtl.GLevel(6)','OpenDivine')
c('ESSBNodes','ESSBReactions.BaseMax(akCtl, aiElement),','ESSBReactions.BaseMax(akCtl, aiElement) * 3.0 * akCtl.GLevel(TreeOf(akCtl.CurrentElement.GetValueInt())),','OnEndReward')
c('ESSBElem3','19, ESSBReactions.BaseMax(akCtl, 11) * aiLayers','19, 25.0 * aiLayers * akCtl.GLevel(10)','OnAstralDetonate')
c('ESSBElem3','4, ESSBReactions.BaseMax(akCtl, 11) * aiLayers','4, 20.0 * aiLayers * akCtl.GLevel(10)','OnAstralDetonate')
c('ESSBController','ESSBReactions.BaseMax(Self, 6)','20.0 * GLevel(5)','TickDomain')
c('ESSBElem3','ESSBReactions.ReactDamage(akCtl, 10, 1.0)','30.0 * akCtl.GetDamageMult(10) * akCtl.GLevel(9)','AfterDeathCurse')
# JudgeArea owns a 100-point unscaled budget. Standalone Judge retains 25.
c('ESSBElem2','Float afMult) Global','Float afMult, Float afHealBase = 25.0) Global','Judge')
c('ESSBElem2','ESSBReactions.ReactDamage(akCtl, 7, 1.0)','afHealBase * akCtl.GetDamageMult(7) * akCtl.GLevel(6)','Judge')
c('ESSBElem2','Int index = 0','Float healLeft = 75.0\n\tInt index = 0','JudgeArea')
c('ESSBElem2','Judge(akCtl, nearby[index], afMult)','Float healBase = 25.0\n\t\t\tIf healBase > healLeft\n\t\t\t\thealBase = healLeft\n\t\t\tEndIf\n\t\t\tJudge(akCtl, nearby[index], afMult, healBase)\n\t\t\thealLeft = healLeft - healBase','JudgeArea')
c('ESSBElem2','HealAllies(akCtl, ESSBReactions.BaseMax(akCtl, 7))','HealAllies(akCtl, 25.0 * akCtl.GLevel(6))','OnDivineHit')
c('ESSBElem2','HealAllies(akCtl, ESSBReactions.BaseMax(akCtl, 7))','HealAllies(akCtl, 40.0 * akCtl.GLevel(6))','OpenDivine')
c('ESSBElem2','4, ESSBReactions.BaseMax(akCtl, 7),','4, 40.0 * akCtl.GLevel(6),','OpenDivine')
c('ESSBController','4, ESSBReactions.BaseMax(Self, 7),','4, 25.0 * GLevel(6),','TickDomain')
c('ESSBController','5, ESSBReactions.BaseMax(Self, 7),','5, 20.0 * GLevel(6),','TickDomain')
c('ESSBElem2','ESSBReactions.ReactDamage(akCtl, 7, 1.0)','25.0 * akCtl.GetDamageMult(7) * akCtl.GLevel(6)','EndDivineNodes')
c('ESSBNoForm','6, 25.0,','6, 60.0 * akCtl.GLevel(11),','OnCombo')
c('ESSBElem3','ESSBReactions.BaseMax(akCtl, 11),','25.0 * akCtl.GLevel(10),','OnAstralHit')
c('ESSBElem3','ESSBReactions.BaseMax(akCtl, 11),','40.0 * akCtl.GLevel(10),','OpenAstral')
c('ESSBReactions','ReactDamage(akCtl, 10, 1.0) * mult','40.0 * akCtl.GetDamageMult(10) * akCtl.GLevel(9) * mult','Open')
c('ESSBElem3','ESSBReactions.ReactDamage(akCtl, 10, 1.0)','30.0 * akCtl.GetDamageMult(10) * akCtl.GLevel(9)','OnDarkHit')
c('ESSBElem3','ESSBReactions.BaseMax(akCtl, 10) * curse','15.0 * curse * akCtl.GLevel(9)','OnKill')
c('ESSBElem3','ESSBReactions.ReactDamage(akCtl, 10, 1.0)','40.0 * akCtl.GetDamageMult(10) * akCtl.GLevel(9)','OnAnyEnd')
c('ESSBReactions','3, 10.0 * mult,','3, 40.0 * akCtl.GLevel(3) * mult,','Open')
c('ESSBReactions','6, 10.0,','6, 40.0 * akCtl.GLevel(3),','Open')
c('ESSBElem2','6, 10.0,','6, 40.0 * akCtl.GLevel(4),','OpenWind')
c('ESSBNodes','* 2.0','* 4.0 * akCtl.GLevel(TreeOf(akCtl.CurrentElement.GetValueInt()))','OnSyncStage')
c('ESSBElem3','ESSBReactions.ReactDamage(akCtl, 9, 2.0) * afMult','ESSBReactions.ReactDamage(akCtl, 9, 2.0) * afMult * akCtl.GLevel(8)','EndWaterNodes')
c('ESSBElem','6, 15.0,','6, 50.0 * akCtl.GLevel(0),','OpenFire')
c('ESSBElem2','ESSBReactions.BaseMax(akCtl, 7) * 2.0','60.0 * akCtl.GLevel(6)','OnFormOpened',2)
c('ESSBElem','ESSBReactions.BaseMax(akCtl, 1) * 2.0','60.0 * akCtl.GLevel(0)','OnIgnite')
c('ESSBElem3','ESSBReactions.BaseMax(akCtl, 10) * 2.0','50.0 * akCtl.GLevel(9)','OnShadowBody')
c('ESSBElem2','ESSBReactions.BaseMax(akCtl, 7) * 2.0','60.0 * akCtl.GLevel(6)','OnAsh')
c('ESSBReactions','ReactDamage(akCtl, 3, 1.0) * mult','60.0 * akCtl.GetDamageMult(3) * akCtl.GLevel(2) * mult','Open')
c('ESSBGuard','ESSBReactions.ReactDamage(Ctl, 3, 1.0)','50.0 * Ctl.GetDamageMult(3) * Ctl.GLevel(2)')
c('ESSBElem','ESSBReactions.BaseMax(akCtl, 3),','60.0 * akCtl.GLevel(2),','OpenShock')
c('ESSBElem2','Return 2.0 * (1.0 + 0.03 * ESSBNodes.Rank(akCtl, 3, 2, 2))','Return 4.0 * (1.0 + 0.03 * ESSBNodes.Rank(akCtl, 3, 2, 2)) * akCtl.GLevel(3)','QuakeStamina')
c('ESSBElem2','Return 30.0 + 2.0 * ESSBNodes.Rank(akCtl, 3, 0, 0)','Return (60.0 + 4.0 * ESSBNodes.Rank(akCtl, 3, 0, 0)) * akCtl.GLevel(3)','FissureArmor')
c('ESSBElem2','Return 15.0','Return 20.0 * akCtl.GLevel(3)','RockArmorPerLayer')
c('ESSBElem2','Return 25.0','Return 25.0 * akCtl.GLevel(3)','RockArmorPerLayer')
c('ESSBElem','amount * drainRatio,','amount * drainRatio * akCtl.GLevel(2),','Discharge')
c('ESSBElem','amount * jumpRatio * drainRatio,','amount * jumpRatio * drainRatio * akCtl.GLevel(2),','Discharge')
c('ESSBElem2','3, 50.0,','3, 80.0 * akCtl.GLevel(3),','OnEarthHit')
c('ESSBElem','ESSBReactions.BaseMax(akCtl, 3) * charge,','ESSBReactions.BaseMax(akCtl, 3) * charge * akCtl.GLevel(2),','OnTick')

for p,s in sources.items():
    Path(p).write_bytes(s.replace('\n',endings[p]).encode('utf-8'))
print('flat amounts + G applied')
