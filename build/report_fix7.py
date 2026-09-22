from pathlib import Path
import re,json,hashlib,html
ROOT=Path(__file__).resolve().parents[1]
audit=(ROOT/'build/flat-values-audit.md').read_text(encoding='utf-8')
rows=[[v.strip() for v in line.strip('|').split('|')] for line in audit.splitlines() if line.startswith('| ')][1:]
assert len(rows)==60
new=[
'50 × 原吸血比 × 開印倍率','B_max ×5 × 原吸血比 × 血位命中倍率','2 秒','1 秒（保留）','1+0.2×rank，原四捨五入及首領折半（保留）',
'1 × rank','15／次','B_max ×2／印記','6／人／秒，最多 5 人','25',
'1.5 × rank','25，低血位 50','25 × 環境 M × 開印 M','20／秒','25／秒',
'25／擊','生命與耐力各 15／秒','2 × rank','B_max ×3','3 × rank',
'25／引爆層','20／引爆層','20／秒','生命與魔力各 30 × 環境 M','25／目標，單次累計 min(25×目標數,100)，再乘環境 M',
'25／同伴／擊','40／同伴','40','生命 25／秒、魔力 20／秒','同 29；同一領域，不另疊加',
'25 × 環境 M／目標','60／三擊','25','40','40 × 原倍率',
'30 × 環境 M','15／詛咒層','40 × 環境 M','40 × 開印倍率','40',
'40','生命與魔力各 B_max ×4','各 B_max ×2 ×afMult（保留基準 14）','50','玩家與同伴各 60',
'60','50','60','60 × 開印倍率','50',
'60','40 ×(1+0.03×rank) ×終焉 M','60+4×rank','20／層','amount ×原削魔比；跳躍仍 ×原跳躍比（保留）',
'80','25／層（保留）','B_max ×charge（保留）','rank≥10 為 1 秒，否則 2 秒（保留）','1 HP（保留）']
assert len(new)==60
# row -> exact producer needle, owning tree, downstream (G-free) delivery.
spec=[
('50.0 * akCtl.GLevel(5)',5,'Leech → ApplyUtil(4/19, abBalanced=True)'),
('* 5.0 * akCtl.GLevel(5)',5,'Leech → ApplyUtil(4/19, abBalanced=True)'),
('SetGuardSwitch(2)',None,'SetGuardSwitch → DurationInt；G 豁免'),
('ApplySilenceSpell(akTarget, 1)',None,'ApplySilenceSpell → DurationInt；G 豁免'),
('Float seconds =',None,'ApplySilenceSpell；G 豁免'),
('1.0 * heal * akCtl.GLevel(6)',6,'ApplyUtil(4)'),
('15.0 * akCtl.GLevel(4)',4,'ApplyUtil(6)'),
('* 2.0 * aiMarks * akCtl.GLevel(11)',11,'ApplyUtil(5)'),
('heal + 6.0 * akCtl.GLevel(7)',7,'heal 累加 → ApplyUtil(4)'),
('25.0 * akCtl.GLevel(7)',7,'ApplyUtil(4)'),
('Float drain = 3.0',3,'drain ×0.5 → ApplyUtil(6)；同來源削耐走 ApplyUtil(3)'),
('Float heal = 25.0',5,'低血位 ×2 → ApplyUtil(4)'),
('25.0 * akCtl.GetDamageMult(7)',6,'ApplyUtil(4)'),
('20.0 * GLevel(0)',0,'ApplyUtil(6)'),
('25.0 * akCtl.GLevel(1)',1,'ApplyUtil(3)'),
('25.0 * akCtl.GLevel(4)',4,'ApplyUtil(6)'),
('ApplyUtil(4, 15.0 * GLevel(8)',8,'生命／耐力各自同一 G → ApplyUtil(4/6)'),
('2.0 * rank * akCtl.GLevel(6)',6,'ApplyUtil(4)'),
('* 3.0 * akCtl.GLevel(TreeOf(', 'current','ApplyUtil(5)；TreeOf(CurrentElement)，非 common 的 12'),
('Float drain = 3.0',3,'ApplyUtil(3)；回耐另取同一未分類 drain ×0.5'),
('25.0 * aiLayers * akCtl.GLevel(10)',10,'ApplyUtil(19)'),
('20.0 * aiLayers * akCtl.GLevel(10)',10,'ApplyUtil(4)'),
('20.0 * GLevel(5)',5,'ApplyUtil(4)'),
('Float gain = 30.0',9,'ApplyUtil(4/5) 各一次，不回寫 gain'),
('afHealBase * akCtl.GetDamageMult(7)',6,'JudgeArea 分配 100 基準預算 → Judge → ApplyUtil(4)'),
('HealAllies(akCtl, 25.0',6,'HealAllies → ApplyUtil(4)；helper 不乘 G'),
('HealAllies(akCtl, 40.0',6,'HealAllies → ApplyUtil(4)'),
('4, 40.0 * akCtl.GLevel(6)',6,'ApplyUtil(4)'),
('ApplyUtil(4, 25.0 * GLevel(6)',6,'生命 25G／魔力 20G → ApplyUtil(4/5)'),
('ApplyUtil(5, 20.0 * GLevel(6)',6,'同 29 的 TickDomain；不重複領域回復'),
('25.0 * akCtl.GetDamageMult(7)',6,'ApplyUtil(4)'),
('60.0 * akCtl.GLevel(11)',11,'ApplyUtil(6)'),
('25.0 * akCtl.GLevel(10)',10,'ApplyUtil(5)'),
('40.0 * akCtl.GLevel(10)',10,'ApplyUtil(5)'),
('Float drain = 40.0',9,'ApplyUtil(2/5) 各一次'),
('Float drain = 30.0',9,'ApplyUtil(2/5) 各一次'),
('15.0 * curse * akCtl.GLevel(9)',9,'ApplyUtil(5)'),
('Float drain = 40.0',9,'ApplyUtil(2/5) 各一次'),
('40.0 * akCtl.GLevel(3) * mult',3,'ApplyUtil(3)'),
('6, 40.0 * akCtl.GLevel(3)',3,'ApplyUtil(6)'),
('40.0 * akCtl.GLevel(4)',4,'ApplyUtil(6)'),
('* 4.0 * akCtl.GLevel(TreeOf(', 'current','amount → ApplyUtil(4/5)；用當前元素樹'),
('Float amount = ESSBReactions.ReactDamage(akCtl, 9, 2.0)',8,'ReactDamage 不乘 G；ApplyUtil(4/6)，不走 ApplyDamage'),
('50.0 * akCtl.GLevel(0)',0,'ApplyUtil(6)'),
('ApplyUtil(4, 60.0 * akCtl.GLevel(6)',6,'玩家 ApplyUtil(4)；同伴 HealAllies → ApplyUtil(4)'),
('60.0 * akCtl.GLevel(0)',0,'ApplyUtil(4)'),
('50.0 * akCtl.GLevel(9)',9,'ApplyUtil(5)'),
('60.0 * akCtl.GLevel(6)',6,'ApplyUtil(5)'),
('60.0 * akCtl.GetDamageMult(3)',2,'ApplyUtil(2)'),
('50.0 * Ctl.GetDamageMult(3)',2,'ApplyUtil(2)'),
('60.0 * akCtl.GLevel(2)',2,'ApplyUtil(5)'),
('Return 4.0 *',3,'QuakeStamina → Quake.stamina → QuakeOne → ApplyUtil(3)；傷害 amount 另一支才進 ApplyDamage'),
('Return (60.0 + 4.0',3,'FissureArmor → Open/OpenEarth → ApplyUtil(1)；擴散不乘開印 M'),
('Return 20.0 * akCtl.GLevel(3)',3,'RockArmorPerLayer → SyncRockArmor → ApplyUtil(18)'),
('amount * drainRatio * akCtl.GLevel(2)',2,'直擊／跳躍 ApplyUtil(2) 各乘一次；amount 本身未乘 G，生命傷害另走 ApplyDamage'),
('80.0 * akCtl.GLevel(3)',3,'ApplyUtil(3)'),
('Return 25.0 * akCtl.GLevel(3)',3,'RockArmorPerLayer → SyncRockArmor → ApplyUtil(18)'),
('* charge * akCtl.GLevel(2)',2,'ApplyUtil(5)；Discharge 不修改呼叫端 charge'),
('Return 1',None,'AstralDelay；固定桶引爆延遲，G／Duration 豁免'),
('RestoreActorValue("Health", 1.0 - player.GetActorValue("Health"))',None,'神佑保命 1 HP，G／Recovery 豁免')]
assert len(spec)==60
proof=[]
for i,(row,sp) in enumerate(zip(rows,spec),1):
    file,fn=row[7].split(':');file=file.removeprefix('src/')
    if i==60:file,fn='ESSBController.psc','RefreshDivineProtection'
    s=(ROOT/'src'/file).read_text(encoding='utf-8')
    m=re.search(r'^[^\n]*\b(?:Function|Event) '+fn+r'\([^\n]*\n.*?^End(?:Function|Event)',s,re.M|re.S)
    assert m,(i,file,fn)
    needle,tree,sink=sp
    hits=[(j,l.strip()) for j,l in enumerate(m[0].splitlines()) if needle in l]
    assert hits,(i,file,fn,needle)
    j,line=hits[0];ln=s[:m.start()].count('\n')+j+1
    if tree is not None:
        expected='GLevel(TreeOf(akCtl.CurrentElement.GetValueInt()))' if tree=='current' else f'GLevel({tree})'
        assert expected in line and line.count('GLevel(')==1,(i,line,expected)
    proof.append(dict(id=f'{i:02}',tree=tree,site=f'src/{file}:{fn}',line=ln,expression=line,sink=sink,G=0 if tree is None else 1))
assert sum(p['G'] for p in proof)==55
(ROOT/'build/fix7-g-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')

def loc(p):return f"`{p['site']}`（行 {p['line']}）"
def esc(s):return str(s).replace('|','／').replace('\n',' ')
out=['\n\n## fix round 7（固定數值與平衡桿）\n',
'範圍：僅固定數值、G(L)、分類倍率與 MCM。未修改規劃、review 文件、fx_extract.py、MO2 或 SkyrimSE；沒有連網。來源 `build/flat-values-audit.md` 共 60 列，以出現順序編號 01–60。',
'\n| 狀態 | 項目 | 結果 |\n|---|---|---|',
'| FIXED | 60 項固定數值 | 按核准建議套用；04、05、43、55、57–60 的基準保留。37 收割為 15／層。 |',
'| FIXED | 裁決／共用領域 | 每目標 25，單次裁決基準累計上限 100；29／30 共用聖域生命 25、魔力 20／秒。 |',
'| FIXED | G(L) | 55 個金額路徑各乘所屬樹 G 一次；5 個時長／保命項豁免。utility 不增乘 G。 |',
'| FIXED | 六類平衡倍率 | 傷害沿用 ESSB_BaseDamageMult；只新增其餘 5 個 float GLOB，各預設 1.0。 |',
'| FIXED | MCM | 一般＝開關、毒／血係數、除錯；平衡＝七支滑桿；技能樹原功能保留。 |',
'| FIXED | 建置及 FormID | 完整 python build_v03.py 成功；3907 舊記錄身分一致、3912 記錄回讀一致；19 支腳本 0 errors。 |',
'| NOT FIXED（核准豁免） | 毒／血層壽命滑桿 | 保留毒 12 格／12 秒、血 10 格／10 秒。固定每秒桶無法容納 3 倍壽命且保留原每秒老化與匯出含義；未改桶、tick 或匯出布局。 |',
'| NOT FIXED（驗證邊界） | 遊戲內實測 | 未操作或寫入正在運行的遊戲；編譯／資料回讀／離線公式測試不代表實際戰鬥或 MCM 畫面已驗證。 |',
'\n數值解讀：下表「新基準」不含新增 G 與分類倍率，保留原環境、層數、開印及終焉倍率。25 的上限採基準預算，最終治療為 `min(25×N,100) × environment × G(divine) × MultRecovery`；預算只限制回血，六目標傷害仍全數結算。11 汲力取 20 削耐的未分類金額一半，故兩類滑桿互不串乘。52 基準以既有土 B_max=10 ×4 表達，保留 settings 的 B 資料源。',
'\n保守解讀與邊界：時長採先乘倍率、正值最短 1 秒，整數法術／倒數器就近四捨五入；0 仍代表取消或永久，不轉成 1 秒。沉默「魔力鎖零／不回魔」、抵消命中與永久復生屬狀態語義，保留既有行為，不把它們變成可漏掉施法的比例削魔；沉默時長可調。冷卻排除 FX／logging／XP 限流及內部排程；每秒輪詢的擴散、雷雨充能和化身仍受原 tick 精度限制，不新增 subsecond tick。星痕引爆延遲依 59 保留。',
'\n| ID | 效果 | 舊基準 | 新基準 | 程式位置 |\n|---|---|---|---|---|']
for i,(r,n,p) in enumerate(zip(rows,new,proof),1):out.append(f'| {i:02} | {esc(r[4])} | {esc(r[5])} | {esc(n)} | {loc(p)} |')
out+=['\n### G(L) 單次縮放證據\n',
'`ESSBTrees.TreeG`＝`1.0 + 0.05 * TreeLevel(aiTree)`。下表列實際可 grep 的來源行與完整 utility 下游；`BaseMax`、`ReactDamage`、`HealAllies`、`Leech`、`ApplyUtil` 均不新增 G。回復／削減分類倍率只處理金額，不回寫 caller 的局部變數。傷害側 `ApplyDamage` 仍只在原 choke point 乘 G；放電的 utility 分支另乘，未提前污染共用 damage amount。',
'\n| ID | 所屬樹 | 唯一 G 來源（原碼） | 下游路徑 | G 次數 |\n|---|---|---|---|---|']
for p in proof:out.append(f"| {p['id']} | {p['tree'] if p['tree'] is not None else '豁免'} | `{esc(p['expression'])}`；{loc(p)} | {esc(p['sink'])} | {p['G']} |")
out+=['\n既有已乘 G 的破魔、反噬及生命傷害不再加第二次；破魔在 `OnManaBreak` 先算 G、再 `DrainAmount`、再限制可吸取魔力，`ApplyUtil(2, ..., True)` 跳過重乘，真傷沿用 `abLevelScaled=True`。百分比治療長流、血盾 20% 上限、抗性百分點不新增 G。',
'\n### 分類倍率與施放位置\n',
'| 分類／GLOB（FormID） | 唯一倍率位置 | 覆蓋呼叫端／例外 |\n|---|---|---|',
'| 傷害／ESSB_BaseDamageMult（00515A；沿用） | ApplyProc、ApplyDamage、ApplyTrueDamage、ApplyUtil(7) | 各為互斥施放終點；ApplyDamageRaw 不增乘。既有元素直傷、真傷與放血；自損／施放代價／Execute 不作可調傷害。 |',
'| 持續傷害／ESSB_MultDot（005168） | ApplyDotDamage；ApplyUtil(7)；EndBlood 的 remaining 項 | Status.Tick 毒／催毒／流血；放血生命比例；TickDomain 死域；血潮只乘剩餘流血、不乘即時生命百分比。 |',
'| 冷卻／ESSB_MultCooldown（005169） | CooldownSeconds | OpenMark、OpenSecond、TakeEndSlot、TakeInterrupt、TakeIceHeart、TakeRetaliate、TakeSanctuary、TakeCleanse、TakePush、Guard.TakeAttacker、雷雨充能、AvatarCooldown、毒擴散、Trees.RespecReady。洗點以 86400 秒換回遊戲日。 |',
'| 回復／ESSB_MultRecovery（00516A） | ApplyUtil(4/5/6/10/11/18/19/25)；Leech→RecoveryAmount（下游 True）；RefreshRecovery；ApplyInherit | 全部玩家／同伴生命魔耐、長流、聖域、血池、潮池；岩甲／血盾／星盾；冰盾／電盾／水鏡／聖盾 PERK 強度；溫血／感應／星輝回復率；血承生命／護甲盾。神佑 1 HP 明確跳過。血盾在乘回復後套原 20% cap。 |',
'| 削減／ESSB_MultDrain（00516B） | ApplyUtil(1/2/3)；OnManaBreak→DrainAmount（下游 True） | 裂痕護甲、感電、放電、深寒、地震、震擊、破魔、蝕魔／暗開印／蝕魔終焉。QuakeOne 判定讀 DrainAmount 以與實際削耐一致；不另乘到 damage 或汲力。抗性百分點與沉默鎖零不變。 |',
'| 持續時間／ESSB_MultDuration（00516C） | DurationSeconds／DurationInt | ApplyMark 同時設定法術與 registry；ApplyUtil 的狀態 duration；ApplyManaBreakMark／ApplySilenceSpell／Fear／Frenzy／Reanimate／Inherit；StartDomain；保留副印記；自身狀態 setter；Status 的 Frozen、Catalyze、DeathCurse、Airborne、StarLock setter 與熱度／凍結／裂痕／失衡／聖印／浸濕／水壓／詛咒到期比較。pending 存原秒數、ImportState 不再縮放。 |',
'\n平衡頁所有 slider 均為 0.25–3.0、step 0.05；冷卻 max=2.0。節點倍率預設沿用 3.0，傷害預設沿用 1.0，五個新增倍率預設 1.0。EDID 不新增 ESSB_MultDamage，避免重複傷害控制與 FormID 改名。',
'\n驗證證據：`build/fix7-build.log`、`build/fix7-check.json`、`build/fix7-g-proof.json`、`build/fix5-mcm-check.json`、`build/v03-compile-results.json`。建置內繼續執行原 DOT、LAYOUT、FIX3、FIX4、MCM、FIX6、READBACK、PLAN、CSF、DELIVERY、PLAN COVERAGE、NODE INDEX、FX 與 ENGINE COVERAGE 檢查；新增 FIX7 檢查 5 GLOB 的型別／預設／VMAD、3907 舊 FormID、不同倍率的實際 utility 公式、裁決 1–6 目標上限、G 來源、固定匯出和編碼。',
'\n檔案編碼／換行：修改的來源沿用 UTF-8（無 BOM）及各檔原 LF／CRLF；`實作紀錄.md` 只在原始位元組尾部追加，原文未重寫。產物位於 `package/Elements Spellblade`，沒有安裝到 MO2 或遊戲。\n']
(ROOT/'build/fix7-report.md').write_text('\n'.join(out),encoding='utf-8')
print('report generated: 60 rows, 55 G paths + 5 exemptions')
