"""Audit only: suggestions never feed settings or source generation."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
plan=json.loads((ROOT/'build/plan-tree-nodes.json').read_text(encoding='utf-8'))
trees={t['id']:t for t in plan['trees']}
rows=[]
def add(tree,r,t,slot,effect,value,site,suggest,reason,score=2,scale='否',name=None):
    if r is None:
        route='基礎反應／狀態';tier='—';node=name;text='第 2.3／2.6 節基礎表（沒有獨立節點）'
    else:
        route=trees[tree]['routes'][r]['name'];tier=trees[tree]['routes'][r]['tiers'][t]['name'];n=trees[tree]['routes'][r]['tiers'][t]
        if slot=='M':node=name or '主線';text=n['main']
        else:b=n['branches'][slot];node=b['name'];text=b['description']
    filename,fn=site.split(':');src=(ROOT/'src'/filename).read_text(encoding='utf-8')
    assert re.search(r'\b(?:Function|Event) '+re.escape(fn)+r'\(',src,re.I),site
    rows.append(dict(tree=tree,route=route,tier=tier,node=node,text=text,effect=effect,value=value,scale=scale,site='src/'+site,suggest=suggest,reason=reason,score=score))
# All amounts below are direct literals or fixed settings B_max, followed through utility delivery (no G).
add('wind',0,2,0,'風刃命中回耐','3／次','ESSBElem2.psc:WindBladeOne','15／次','3 只占 200–400 耐力的 0.75–1.5%；提高到可抵一部分攻擊成本',.75)
add('earth',0,2,0,'命中削耐的一半回耐','0.25 × rank，滿點 3.75／擊','ESSBElem2.psc:OnEarthHit','1.5 × rank，滿點 22.5','目前滿點回復不到 400 耐力的 1%',.94)
add('divine',0,2,'M','B_max 固定基準命中回血','10 × 0.02 × rank，滿點 3／擊','ESSBElem2.psc:OnDivineHit','每點 1 HP，滿點 15／擊','現值滿點僅 300–500 HP 的 0.6–1%；不是最大生命百分比',.6)
add('poison',1,3,1,'開印回血','B_max 9 × 0.5 = 4.5','ESSBElem3.psc:OpenPoison','25','一次僅 0.9–1.5% 最大生命',.9)
add('poison',0,4,0,'附近每名中毒敵人每秒回血','4.5／人／秒，最多 5 人 = 22.5','ESSBElem3.psc:PoisonFormTick','6／人／秒，最多 30','單敵偏弱；五敵現值已可感受，避免直接乘六',.9)
add('blood',1,1,1,'開印固定回血','10 × 0.5 = 5；低血位 ×2 = 10','ESSBElem2.psc:OpenBlood','25；低血位 50','目前 1–3.3% HP，低血位救急偏弱',1)
add('wind',0,1,1,'命中回耐','5／擊','ESSBElem2.psc:OnWindHit','25／擊','僅 1.25–2.5% 耐力',1.25)
add('fire',0,2,1,'熔身每秒回耐','5／秒 ×10 秒 = 50','ESSBController.psc:TickTimers','20／秒','每秒僅 1.25–2.5%，完整十秒才累積可見',1.25)
add('frost',0,1,0,'冰封期間每秒削耐','5／秒','ESSBElem.psc:OnFrozenTick','25／秒','目前不足抵銷高耐力敵人的續戰；文字「不回復」實際是定量削減',1.25)
add('blood',None,None,None,'命中流血目標吸血（固定 B 基準）','B_max 10 × 吸血比 × 血位命中倍率；基礎滿血 0.65，低血 3；吸血主線滿點滿血 2.6、低血 3.9','ESSBElem2.psc:OnBloodHit','基準改為 B_max ×5 再乘原比率','這裡沒有讀實際附傷；高血量下每擊往往不到 1%',.13,name='基礎吸血')
add('blood',None,None,None,'血痕開印吸血','10 × 吸血比 × 開印倍率；基礎 0.5–5','ESSBReactions.psc:Open','固定基準 50 × 原比率','即使顯示吸血比例，取的是固定 B，並非目標生命或實傷',.1,name='血痕')
add('water',2,4,0,'水域每秒回生命與耐力','各 B_max = 7／秒，5 秒各 35','ESSBController.psc:TickDomain','各 15／秒','7 點相對新長流很小；仍維持領域只是附加收益',1.4)
add('divine',1,0,'M','開印額外回血','10 × 0.05 × rank，滿點 7.5','ESSBElem2.psc:OpenDivine','每點 2，滿點 30','不是最大生命 5%；滿點也僅 1.5–2.5% HP',1.5)
add('divine',None,None,None,'聖印開印基礎回血','B_max 10 ×0.5 ×環境 M ×開印 M；無分支滿點白天 8.7、夜晚 7.25','ESSBReactions.psc:Open','基準 25，再乘原倍率','基礎 5 HP，且 ApplyUtil 不乘 G',1,name='聖印')
add('earth',0,2,'M','每擊固定削耐','0.5 × rank；滿點 7.5','ESSBElem2.psc:OnEarthHit','3 × rank；滿點 45','滿點對 200–400 耐力只削 1.9–3.8%',1.875)
add('earth',None,None,None,'裂痕開印削耐','10 × 開印倍率（滿點 14.5）','ESSBReactions.psc:Open','40 × 開印倍率','原基準只有 2.5–5% 耐力',2.5,name='裂痕')
add('earth',None,None,None,'裂痕開印回耐','10','ESSBReactions.psc:Open','40','一次只有 2.5–5% 耐力',2.5,name='裂痕')
add('wind',1,3,1,'開印回耐','10','ESSBElem2.psc:OpenWind','40','可支援一次明顯的重擊／衝刺消耗',2.5)
add('blood',2,4,0,'血池每秒回血','B_max 10／秒，5 秒共 50','ESSBController.psc:TickDomain','20／秒','現值持續站滿已有 10–16.7% HP；建議只加倍',2)
add('divine',0,3,0,'命中治療每名同伴','B_max 10／擊','ESSBElem2.psc:OnDivineHit','25／擊','對 300–500 HP 同伴僅 2–3.3%',2)
add('divine',1,3,1,'開印治療每名同伴','B_max 10','ESSBElem2.psc:OpenDivine','40','低頻開印應比每擊回復更明顯',2)
add('divine',2,3,1,'聖引預約下一開印治療玩家','B_max 10','ESSBElem2.psc:OpenDivine','40','需終焉再開印，條件成本高',2)
add('divine',2,2,0,'聖域每秒回生命與魔力','各 B_max 10／秒，5 秒各 50','ESSBController.psc:TickDomain','生命 25／秒、魔力 20／秒','目前單體神聖續戰治療低於新長流',2)
add('divine',2,4,0,'神聖領域同一回復路徑，延長時長','各 10／秒，8 秒各 80','ESSBController.psc:TickDomain','沿用聖域建議，不另疊加','兩個節點共用同一領域；目前已有 8 秒累積價值',2)
add('divine',None,None,None,'裁決回血（每名被裁決目標各一次）','B_max 10 ×環境 M，白天 12／次；範圍最多 6 次 = 72','ESSBElem2.psc:Judge','單體 25 ×環境 M；群體需另評估','單體偏低，但六目標已有明顯爆發，不宜照單體盲目翻倍',2,name='裁決')
add('divine',2,1,1,'聖印記融斷每目標額外治療','10 ×環境 M，白天 12','ESSBElem2.psc:EndDivineNodes','25 ×環境 M','現值約 2–4% HP；注意多目標總和',2)
add('darkness',0,0,0,'命中詛咒目標吸魔／回魔','B_max 10 ×環境 M，夜晚 12','ESSBElem3.psc:OnDarkHit','30 ×環境 M','只有 2.5–6% 的 200–400 魔力',2.5)
add('darkness',None,None,None,'詛咒開印吸魔／回魔','10 ×環境 M ×開印 M；滿點夜晚 17.4','ESSBReactions.psc:Open','40 ×原倍率','有開印間隔，基準 10 太小；不隨 G 成長',2.5,name='詛咒')
add('darkness',2,0,0,'死咒結算吸血與吸魔','各 10 ×環境 M（夜晚 12）','ESSBElem3.psc:AfterDeathCurse','各 30 ×環境 M','延遲後回復僅約 2–6% 資源',2)
add('darkness',2,1,1,'蝕魔終焉預約下一終焉吸魔／回魔','10 ×環境 M（夜晚 12）','ESSBElem3.psc:OnAnyEnd','40 ×環境 M','需要跨終焉觸發，回報應更明顯',2.5)
add('darkness',0,3,1,'詛咒目標死亡回魔','B_max 10 ×詛咒層數，1–13 層 = 10–130','ESSBElem3.psc:OnKill','15／層','低層偏小，但滿層已明顯；勿整體 ×3',2.5)
add('astral',0,1,1,'命中回魔','B_max 10','ESSBElem3.psc:OnAstralHit','25','約 2.5–5% 魔力',2.5)
add('astral',1,1,1,'開印回魔','B_max 10','ESSBElem3.psc:OpenAstral','40','低頻開印僅 2.5–5% 魔力',2.5)
add('astral',0,3,1,'引爆臨時生命護盾','B_max 10 ×當次引爆層數，10 秒；同款 Peak Value Modifier 不逐次相加','ESSBElem3.psc:OnAstralDetonate','25／引爆層','單層盾僅 2–3.3% HP，容易毫無感覺',2)
add('astral',0,4,0,'星痕引爆回血','B_max 10 ×當次層數','ESSBElem3.psc:OnAstralDetonate','20／層','單層僅 2–3.3% HP；連續引爆仍可累積',2)
add('fire',1,1,1,'開印回耐','15','ESSBElem.psc:OpenFire','50','3.75–7.5% 耐力，低頻開印收益仍小',3.75)
add('divine',0,2,1,'化灰回魔','B_max 10 ×2 = 20','ESSBElem2.psc:OnAsh','60','擊殺且化灰條件下僅 5–10% 魔力',5)
add('divine',1,2,0,'聖臨時玩家與附近同伴回血','各 B_max 10 ×2 = 20','ESSBElem2.psc:OnFormOpened','各 60','開形態事件較低頻，20 HP 僅 4–6.7%',4)
add('darkness',0,4,0,'影身觸發回魔','B_max 10 ×2 = 20','ESSBElem3.psc:OnShadowBody','50','另有受擊／機率門檻，回魔量偏小',5)
add('fire',0,3,1,'自燃回血','B_max 12 ×2 = 24','ESSBElem.psc:OnIgnite','60','需累積熱度才觸發，24 HP 為 4.8–8%',4.8)
add('lightning',1,1,1,'開印回魔','B_max 25','ESSBElem.psc:OpenShock','60','約 6.25–12.5%；已較其他樹明顯',6.25)
add('lightning',0,1,1,'被近戰命中時感電削魔','B_max 25','ESSBGuard.psc:OnHitEx','50','受擊才觸發，對高魔力敵人效果有限',6.25)
add('lightning',None,None,None,'感電開印削魔','B_max 25 ×開印倍率，滿點 36.25','ESSBReactions.psc:Open','60 ×開印倍率','基準 25，不乘 G，與新破魔落差極大',6.25,name='感電')
add('noform',0,2,0,'連續三次命中回耐','25／三擊','ESSBNoForm.psc:OnCombo','60／三擊','平均 8.33／擊，約 2.1–4.2% 耐力',2.08)
add('noform',2,3,1,'融斷每個印記回魔','B_max ×0.5；依元素 = 3.5–12.5／印記','ESSBNoForm.psc:OnBurst','B_max ×2／印記','水印記只給 3.5，低於 400 魔力的 1%',.875)
add('common',0,3,1,'同調升段回生命與魔力','各 B_max ×2；依元素 = 14–50','ESSBNodes.psc:OnSyncStage','各 B_max ×4','每場升段有限；水基準只回 14',2.8)
add('common',2,1,0,'每次終焉回魔','B_max；依元素 = 7–25','ESSBNodes.psc:OnEndReward','B_max ×3','最低僅 1.75% 的 400 魔力',1.75)
add('earth',None,None,None,'裂痕削甲（主線追加）','30 +2 ×rank；滿點 60，再乘開印 M；擴散目標不乘開印 M','ESSBElem2.psc:FissureArmor','60 +4 ×rank；滿點 120','沒有 G；單靠 30–60 護甲差距較不顯眼',8,name='裂痕／持續新手主線')
add('earth',None,None,None,'每層岩甲護甲','15／層；基礎 5 層 = 75；萬象後 8 層 =120','ESSBElem2.psc:RockArmorPerLayer','20／層','單層 15 偏弱，但滿層已有價值，避免大幅提升',8,name='岩甲')
add('earth',0,0,0,'磐石每層岩甲護甲','25／層；厚土＋萬象最多 13 層 =325','ESSBElem2.psc:RockArmorPerLayer','保留 25','滿層 325 已明顯，不能只看單層小就上調',20)
add('earth',0,1,0,'重擊消耗裂痕額外削耐','50','ESSBElem2.psc:OnEarthHit','80','對 200–400 耐力削 12.5–25%，其實已有感',12.5)
add('earth',2,2,'M','地震削耐基準及主線','B_max 10 ×2 ×(1+0.03×rank) ×終焉 M；rank15 基準29','ESSBElem2.psc:QuakeStamina','基準 40，保留 +3%／點','沒有 G，但新終焉倍率已提高實際值，需先實測再調',7.25)
add('lightning',0,4,0,'滿電荷自動放電回魔','B_max 25 ×charge；基礎 cap6=150；主線＋萬象 cap14=350','ESSBElem.psc:OnTick','保留','高層數已接近回滿 200–400 魔力，不属於小數值問題',37.5)
add('lightning',None,None,None,'放電削魔及跳躍削魔','傷害未乘 G 的 amount ×0.5（電蝕 1.0）；跳躍再 ×0.4（電弧 0.8）；B_max=25','ESSBElem.psc:Discharge','暫留；先驗新節點倍率','不是實際生命傷害的一半，沒有 G；但電荷與終焉節點可放大很多',10,name='放電')
add('water',2,1,1,'水印記融斷治療與回耐','各 B_max 7 ×2 ×afMult；倍率中含新通用／元素／無形態融斷節點','ESSBElem3.psc:EndWaterNodes','暫留基準 14','雖基準低，但整條融斷倍率已 ×3，需避免二次過度放大',2.8)
# Short durations: actual runtime values, not stale design prose. Exclude infrastructure timers.
add('common',1,1,0,'切換受傷 -50% 視窗','1 秒','ESSBController.psc:SwitchForm','2 秒','紙面強但 1 秒受排程與攻擊節奏影響，容易錯過',.5)
add('noform',1,1,0,'斷咒附帶沉默','1 秒（每 5 秒至多一次）','ESSBNoForm.psc:OnManaBreak','2 秒','僅盤點：第 2 項明定沉默時長不改',.5)
add('noform',1,2,'M','低點數沉默及首領折半','1+0.2×rank，四捨五入；rank1–2 實際 1 秒，首領最少1秒','ESSBNoForm.psc:ApplySilence','暫留','明確按使用者要求不改；低點數體感弱不是破魔削量問題',.5)
add('astral',1,0,'M','高點數星痕引爆延遲','rank≥10 時 1 秒；否則2秒','ESSBElem3.psc:AstralDelay','保留','這是更快引爆的收益，短時長並非弱點',50)
add('divine',0,4,0,'神佑救命瞬間回血','1 HP，另給2秒守護','ESSBGuard.psc:OnHitEx','保留1','這是保命觸發語義，不是普通補血，不應機械放大',100)
rows.sort(key=lambda x:(x['score'],x['tree'],x['route']))
# Capture all delivery candidates including excluded percentage/level-scaled paths for reproducibility.
scan=[]
for p in (ROOT/'src').glob('*.psc'):
    fn='';kind=''
    for i,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
        m=re.search(r'\b(Function|Event) (\w+)\(',line,re.I)
        if m:kind,fn=m.groups()
        if line.lstrip().startswith(';'):continue
        if re.search(r'ApplyUtil\(|ApplyDamage\(|ApplyTrueDamage\(|ApplyBleedDrain\(|SetGuardSwitch\(|ApplySilenceSpell\(|RockArmorPerLayer\(',line):
            scan.append(dict(file=str(p.relative_to(ROOT)),function=fn,line=i,source=line.strip()))
(ROOT/'build/flat-values-audit-source.json').write_text(json.dumps(dict(rows=rows,delivery_scan=scan),ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 固定數值盤點（僅建議，未套用）','','基準：角色 40 級以上，生命 300–500、耐力／魔力 200–400，敵人生命 500–2000。依「單次效果占資源比例／觸發成本」由最不顯眼排序；不同資源與時長的排序是判斷，不是假裝存在統一精準分數。', '', '來源為 src/*.psc 實際公式及 settings.json 的 B_max，並逐項對照節點資料。B_max 的比例仍是固定點數基準，不是角色最大資源百分比，因此列入。除 rank／層數／既有節點倍率外，表內金額均不隨樹等級或 G(L) 成長。涉及第 2／2b 項已修改的破魔金額、長流、清流、回流及減速數值已排除；時長未改者照列。', '', '「固定傷害」檢查結果：沒有額外的生命固定傷害候選；基礎反應、附傷、風刃、星痕、毒／血 DoT 走 ApplyDamage 或 ApplyProc 並乘 G；破魔以外真傷走 ApplyTrueDamage。放血、血潮生命項、死咒生命項是生命百分比，排除。反噬回魔明確乘 GLevel(11)，排除。魔抗／元素抗性 AV 的 10、15、50 是百分點，不是平坦吸收點數，排除；血盾依溢出與最大生命比例，亦排除。', '', '夢魘文字 1.5 秒實作為 2 秒，預知文字「前1秒」實作守護 2 秒，浮空舊註解 1.5 秒目前掛 2 秒：均不列為實際小於2秒。復生攻擊加成使用 AttackDamageMult AV 的百分點，不是平坦武器傷害；0.15秒浮空排程、0.5秒 tick、推力數字、冷卻、層數、距離與等級閾值不是本表的資源量或效果時長。', '',f'共 {len(rows)} 列，涵蓋 {len(set(r["tree"] for r in rows))}/13 樹；完整 delivery 掃描存於 build/flat-values-audit-source.json。所有「建議值」均未修改到模組。','', '| 樹 | 路線 | 階 | 節點／分支（原文對照） | 效果 | 現值 | 隨樹等級／G(L)？ | 程式位置 | 建議值與理由 |','|---|---|---|---|---|---|---|---|---|']
for r in rows:
    lines.append('| '+' | '.join(str(x).replace('|','／').replace('\n',' ') for x in [r['tree'],r['route'],r['tier'],r['node']+'：'+r['text'],r['effect'],r['value'],r['scale'],r['site'],r['suggest']+'；'+r['reason']])+' |')
(ROOT/'build/flat-values-audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('FLAT AUDIT',len(rows),'rows',len(set(r['tree'] for r in rows)),'trees')
