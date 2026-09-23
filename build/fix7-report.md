

## fix round 7（固定數值與平衡桿）

範圍：僅固定數值、G(L)、分類倍率與 MCM。未修改規劃、review 文件、fx_extract.py、MO2 或 SkyrimSE；沒有連網。來源 `build/flat-values-audit.md` 共 60 列，以出現順序編號 01–60。

| 狀態 | 項目 | 結果 |
|---|---|---|
| FIXED | 60 項固定數值 | 按核准建議套用；04、05、43、55、57–60 的基準保留。37 收割為 15／層。 |
| FIXED | 裁決／共用領域 | 每目標 25，單次裁決基準累計上限 100；29／30 共用聖域生命 25、魔力 20／秒。 |
| FIXED | G(L) | 55 個金額路徑各乘所屬樹 G 一次；5 個時長／保命項豁免。utility 不增乘 G。 |
| FIXED | 六類平衡倍率 | 傷害沿用 ESSB_BaseDamageMult；只新增其餘 5 個 float GLOB，各預設 1.0。 |
| FIXED | MCM | 一般＝開關、毒／血係數、除錯；平衡＝七支滑桿；技能樹原功能保留。 |
| FIXED | 建置及 FormID | 完整 python build_v03.py 成功；3907 舊記錄身分一致、3912 記錄回讀一致；19 支腳本 0 errors。 |
| NOT FIXED（核准豁免） | 毒／血層壽命滑桿 | 保留毒 12 格／12 秒、血 10 格／10 秒。固定每秒桶無法容納 3 倍壽命且保留原每秒老化與匯出含義；未改桶、tick 或匯出布局。 |
| NOT FIXED（驗證邊界） | 遊戲內實測 | 未操作或寫入正在運行的遊戲；編譯／資料回讀／離線公式測試不代表實際戰鬥或 MCM 畫面已驗證。 |

數值解讀：下表「新基準」不含新增 G 與分類倍率，保留原環境、層數、開印及終焉倍率。25 的上限採基準預算，最終治療為 `min(25×N,100) × environment × G(divine) × MultRecovery`；預算只限制回血，六目標傷害仍全數結算。11 汲力取 20 削耐的未分類金額一半，故兩類滑桿互不串乘。52 基準以既有土 B_max=10 ×4 表達，保留 settings 的 B 資料源。

保守解讀與邊界：時長採先乘倍率、正值最短 1 秒，整數法術／倒數器就近四捨五入；0 仍代表取消或永久，不轉成 1 秒。沉默「魔力鎖零／不回魔」、抵消命中與永久復生屬狀態語義，保留既有行為，不把它們變成可漏掉施法的比例削魔；沉默時長可調。冷卻排除 FX／logging／XP 限流及內部排程；每秒輪詢的擴散、雷雨充能和化身仍受原 tick 精度限制，不新增 subsecond tick。星痕引爆延遲依 59 保留。

| ID | 效果 | 舊基準 | 新基準 | 程式位置 |
|---|---|---|---|---|
| 01 | 血痕開印吸血 | 10 × 吸血比 × 開印倍率；基礎 0.5–5 | 50 × 原吸血比 × 開印倍率 | `src/ESSBReactions.psc:Open`（行 103） |
| 02 | 命中流血目標吸血（固定 B 基準） | B_max 10 × 吸血比 × 血位命中倍率；基礎滿血 0.65，低血 3；吸血主線滿點滿血 2.6、低血 3.9 | B_max ×5 × 原吸血比 × 血位命中倍率 | `src/ESSBElem2.psc:OnBloodHit`（行 225） |
| 03 | 切換受傷 -50% 視窗 | 1 秒 | 2 秒 | `src/ESSBController.psc:SwitchForm`（行 1391） |
| 04 | 斷咒附帶沉默 | 1 秒（每 5 秒至多一次） | 1 秒（保留） | `src/ESSBNoForm.psc:OnManaBreak`（行 189） |
| 05 | 低點數沉默及首領折半 | 1+0.2×rank，四捨五入；rank1–2 實際 1 秒，首領最少1秒 | 1+0.2×rank，原四捨五入及首領折半（保留） | `src/ESSBNoForm.psc:ApplySilence`（行 202） |
| 06 | B_max 固定基準命中回血 | 10 × 0.02 × rank，滿點 3／擊 | 1 × rank | `src/ESSBElem2.psc:OnDivineHit`（行 237） |
| 07 | 風刃命中回耐 | 3／次 | 15／次 | `src/ESSBElem2.psc:WindBladeOne`（行 600） |
| 08 | 融斷每個印記回魔 | B_max ×0.5；依元素 = 3.5–12.5／印記 | B_max ×2／印記 | `src/ESSBNoForm.psc:OnBurst`（行 341） |
| 09 | 附近每名中毒敵人每秒回血 | 4.5／人／秒，最多 5 人 = 22.5 | 6／人／秒，最多 5 人 | `src/ESSBElem3.psc:PoisonFormTick`（行 1095） |
| 10 | 開印回血 | B_max 9 × 0.5 = 4.5 | 25 | `src/ESSBElem3.psc:OpenPoison`（行 347） |
| 11 | 命中削耐的一半回耐 | 0.25 × rank，滿點 3.75／擊 | 1.5 × rank | `src/ESSBElem2.psc:OnEarthHit`（行 178） |
| 12 | 開印固定回血 | 10 × 0.5 = 5；低血位 ×2 = 10 | 25，低血位 50 | `src/ESSBElem2.psc:OpenBlood`（行 356） |
| 13 | 聖印開印基礎回血 | B_max 10 ×0.5 ×環境 M ×開印 M；無分支滿點白天 8.7、夜晚 7.25 | 25 × 環境 M × 開印 M | `src/ESSBReactions.psc:Open`（行 108） |
| 14 | 熔身每秒回耐 | 5／秒 ×10 秒 = 50 | 20／秒 | `src/ESSBController.psc:TickTimers`（行 4009） |
| 15 | 冰封期間每秒削耐 | 5／秒 | 25／秒 | `src/ESSBElem.psc:OnFrozenTick`（行 513） |
| 16 | 命中回耐 | 5／擊 | 25／擊 | `src/ESSBElem2.psc:OnWindHit`（行 210） |
| 17 | 水域每秒回生命與耐力 | 各 B_max = 7／秒，5 秒各 35 | 生命與耐力各 15／秒 | `src/ESSBController.psc:TickDomain`（行 4767） |
| 18 | 開印額外回血 | 10 × 0.05 × rank，滿點 7.5 | 2 × rank | `src/ESSBElem2.psc:OpenDivine`（行 386） |
| 19 | 每次終焉回魔 | B_max；依元素 = 7–25 | B_max ×3 | `src/ESSBNodes.psc:OnEndReward`（行 248） |
| 20 | 每擊固定削耐 | 0.5 × rank；滿點 7.5 | 3 × rank | `src/ESSBElem2.psc:OnEarthHit`（行 178） |
| 21 | 引爆臨時生命護盾 | B_max 10 ×當次引爆層數，10 秒；同款 Peak Value Modifier 不逐次相加 | 25／引爆層 | `src/ESSBElem3.psc:OnAstralDetonate`（行 857） |
| 22 | 星痕引爆回血 | B_max 10 ×當次層數 | 20／引爆層 | `src/ESSBElem3.psc:OnAstralDetonate`（行 861） |
| 23 | 血池每秒回血 | B_max 10／秒，5 秒共 50 | 20／秒 | `src/ESSBController.psc:TickDomain`（行 4762） |
| 24 | 死咒結算吸血與吸魔 | 各 10 ×環境 M（夜晚 12） | 生命與魔力各 30 × 環境 M | `src/ESSBElem3.psc:AfterDeathCurse`（行 653） |
| 25 | 裁決回血（每名被裁決目標各一次） | B_max 10 ×環境 M，白天 12／次；範圍最多 6 次 = 72 | 25／目標，單次累計 min(25×目標數,100)，再乘環境 M | `src/ESSBElem2.psc:Judge`（行 720） |
| 26 | 命中治療每名同伴 | B_max 10／擊 | 25／同伴／擊 | `src/ESSBElem2.psc:OnDivineHit`（行 254） |
| 27 | 開印治療每名同伴 | B_max 10 | 40／同伴 | `src/ESSBElem2.psc:OpenDivine`（行 402） |
| 28 | 聖引預約下一開印治療玩家 | B_max 10 | 40 | `src/ESSBElem2.psc:OpenDivine`（行 406） |
| 29 | 聖域每秒回生命與魔力 | 各 B_max 10／秒，5 秒各 50 | 生命 25／秒、魔力 20／秒 | `src/ESSBController.psc:TickDomain`（行 4764） |
| 30 | 神聖領域同一回復路徑，延長時長 | 各 10／秒，8 秒各 80 | 同 29；同一領域，不另疊加 | `src/ESSBController.psc:TickDomain`（行 4765） |
| 31 | 聖印記融斷每目標額外治療 | 10 ×環境 M，白天 12 | 25 × 環境 M／目標 | `src/ESSBElem2.psc:EndDivineNodes`（行 880） |
| 32 | 連續三次命中回耐 | 25／三擊 | 60／三擊 | `src/ESSBNoForm.psc:OnCombo`（行 101） |
| 33 | 命中回魔 | B_max 10 | 25 | `src/ESSBElem3.psc:OnAstralHit`（行 303） |
| 34 | 開印回魔 | B_max 10 | 40 | `src/ESSBElem3.psc:OpenAstral`（行 430） |
| 35 | 詛咒開印吸魔／回魔 | 10 ×環境 M ×開印 M；滿點夜晚 17.4 | 40 × 原倍率 | `src/ESSBReactions.psc:Open`（行 121） |
| 36 | 命中詛咒目標吸魔／回魔 | B_max 10 ×環境 M，夜晚 12 | 30 × 環境 M | `src/ESSBElem3.psc:OnDarkHit`（行 259） |
| 37 | 詛咒目標死亡回魔 | B_max 10 ×詛咒層數，1–13 層 = 10–130 | 15／詛咒層 | `src/ESSBElem3.psc:OnKill`（行 1189） |
| 38 | 蝕魔終焉預約下一終焉吸魔／回魔 | 10 ×環境 M（夜晚 12） | 40 × 環境 M | `src/ESSBElem3.psc:OnAnyEnd`（行 1054） |
| 39 | 裂痕開印削耐 | 10 × 開印倍率（滿點 14.5） | 40 × 開印倍率 | `src/ESSBReactions.psc:Open`（行 92） |
| 40 | 裂痕開印回耐 | 10 | 40 | `src/ESSBReactions.psc:Open`（行 93） |
| 41 | 開印回耐 | 10 | 40 | `src/ESSBElem2.psc:OpenWind`（行 329） |
| 42 | 同調升段回生命與魔力 | 各 B_max ×2；依元素 = 14–50 | 生命與魔力各 B_max ×4 | `src/ESSBNodes.psc:OnSyncStage`（行 120） |
| 43 | 水印記融斷治療與回耐 | 各 B_max 7 ×2 ×afMult；倍率中含新通用／元素／無形態融斷節點 | 各 B_max ×2 ×afMult（保留基準 14） | `src/ESSBElem3.psc:EndWaterNodes`（行 996） |
| 44 | 開印回耐 | 15 | 50 | `src/ESSBElem.psc:OpenFire`（行 248） |
| 45 | 聖臨時玩家與附近同伴回血 | 各 B_max 10 ×2 = 20 | 玩家與同伴各 60 | `src/ESSBElem2.psc:OnFormOpened`（行 468） |
| 46 | 自燃回血 | B_max 12 ×2 = 24 | 60 | `src/ESSBElem.psc:OnIgnite`（行 404） |
| 47 | 影身觸發回魔 | B_max 10 ×2 = 20 | 50 | `src/ESSBElem3.psc:OnShadowBody`（行 1249） |
| 48 | 化灰回魔 | B_max 10 ×2 = 20 | 60 | `src/ESSBElem2.psc:OnAsh`（行 1043） |
| 49 | 感電開印削魔 | B_max 25 ×開印倍率，滿點 36.25 | 60 × 開印倍率 | `src/ESSBReactions.psc:Open`（行 87） |
| 50 | 被近戰命中時感電削魔 | B_max 25 | 50 | `src/ESSBGuard.psc:OnHitEx`（行 196） |
| 51 | 開印回魔 | B_max 25 | 60 | `src/ESSBElem.psc:OpenShock`（行 305） |
| 52 | 地震削耐基準及主線 | B_max 10 ×2 ×(1+0.03×rank) ×終焉 M；rank15 基準29 | 40 ×(1+0.03×rank) ×終焉 M | `src/ESSBElem2.psc:QuakeStamina`（行 494） |
| 53 | 裂痕削甲（主線追加） | 30 +2 ×rank；滿點 60，再乘開印 M；擴散目標不乘開印 M | 60+4×rank | `src/ESSBElem2.psc:FissureArmor`（行 416） |
| 54 | 每層岩甲護甲 | 15／層；基礎 5 層 = 75；萬象後 8 層 =120 | 20／層 | `src/ESSBElem2.psc:RockArmorPerLayer`（行 31） |
| 55 | 放電削魔及跳躍削魔 | 傷害未乘 G 的 amount ×0.5（電蝕 1.0）；跳躍再 ×0.4（電弧 0.8）；B_max=25 | amount ×原削魔比；跳躍仍 ×原跳躍比（保留） | `src/ESSBElem.psc:Discharge`（行 539） |
| 56 | 重擊消耗裂痕額外削耐 | 50 | 80 | `src/ESSBElem2.psc:OnEarthHit`（行 191） |
| 57 | 磐石每層岩甲護甲 | 25／層；厚土＋萬象最多 13 層 =325 | 25／層（保留） | `src/ESSBElem2.psc:RockArmorPerLayer`（行 29） |
| 58 | 滿電荷自動放電回魔 | B_max 25 ×charge；基礎 cap6=150；主線＋萬象 cap14=350 | B_max ×charge（保留） | `src/ESSBElem.psc:OnTick`（行 779） |
| 59 | 高點數星痕引爆延遲 | rank≥10 時 1 秒；否則2秒 | rank≥10 為 1 秒，否則 2 秒（保留） | `src/ESSBElem3.psc:AstralDelay`（行 832） |
| 60 | 神佑救命瞬間回血 | 1 HP，另給2秒守護 | 1 HP（保留） | `src/ESSBController.psc:RefreshDivineProtection`（行 7548） |

### G(L) 單次縮放證據

`ESSBTrees.TreeG`＝`1.0 + 0.05 * TreeLevel(aiTree)`。下表列實際可 grep 的來源行與完整 utility 下游；`BaseMax`、`ReactDamage`、`HealAllies`、`Leech`、`ApplyUtil` 均不新增 G。回復／削減分類倍率只處理金額，不回寫 caller 的局部變數。傷害側 `ApplyDamage` 仍只在原 choke point 乘 G；放電的 utility 分支另乘，未提前污染共用 damage amount。

| ID | 所屬樹 | 唯一 G 來源（原碼） | 下游路徑 | G 次數 |
|---|---|---|---|---|
| 01 | 5 | `akCtl.Leech(50.0 * akCtl.GLevel(5) * akCtl.GetBloodLeechRatio() * mult)`；`src/ESSBReactions.psc:Open`（行 103） | Leech → ApplyUtil(4/19, abBalanced=True) | 1 |
| 02 | 5 | `Float amount = ESSBReactions.BaseMax(akCtl, 6) * 5.0 * akCtl.GLevel(5) * akCtl.GetBloodLeechRatio() * akCtl.GetDamageMult(6)`；`src/ESSBElem2.psc:OnBloodHit`（行 225） | Leech → ApplyUtil(4/19, abBalanced=True) | 1 |
| 03 | 豁免 | `SetGuardSwitch(2)`；`src/ESSBController.psc:SwitchForm`（行 1391） | SetGuardSwitch → DurationInt；G 豁免 | 0 |
| 04 | 豁免 | `akCtl.ApplySilenceSpell(akTarget, 1)`；`src/ESSBNoForm.psc:OnManaBreak`（行 189） | ApplySilenceSpell → DurationInt；G 豁免 | 0 |
| 05 | 豁免 | `Float seconds = 1.0 + 0.2 * rank`；`src/ESSBNoForm.psc:ApplySilence`（行 202） | ApplySilenceSpell；G 豁免 | 0 |
| 06 | 6 | `akCtl.ApplyUtil(4, 1.0 * heal * akCtl.GLevel(6), 0, player)`；`src/ESSBElem2.psc:OnDivineHit`（行 237） | ApplyUtil(4) | 1 |
| 07 | 4 | `akCtl.ApplyUtil(6, 15.0 * akCtl.GLevel(4), 0, player)`；`src/ESSBElem2.psc:WindBladeOne`（行 600） | ApplyUtil(6) | 1 |
| 08 | 11 | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, aiElement) * 2.0 * aiMarks * akCtl.GLevel(11), 0, player)`；`src/ESSBNoForm.psc:OnBurst`（行 341） | ApplyUtil(5) | 1 |
| 09 | 7 | `heal = heal + 6.0 * akCtl.GLevel(7)`；`src/ESSBElem3.psc:PoisonFormTick`（行 1095） | heal 累加 → ApplyUtil(4) | 1 |
| 10 | 7 | `akCtl.ApplyUtil(4, 25.0 * akCtl.GLevel(7), 0, player)`；`src/ESSBElem3.psc:OpenPoison`（行 347） | ApplyUtil(4) | 1 |
| 11 | 3 | `Float drain = 3.0 * ESSBNodes.Rank(akCtl, 3, 0, 2) * akCtl.GLevel(3)`；`src/ESSBElem2.psc:OnEarthHit`（行 178） | drain ×0.5 → ApplyUtil(6)；同來源削耐走 ApplyUtil(3) | 1 |
| 12 | 5 | `Float heal = 25.0 * akCtl.GLevel(5)`；`src/ESSBElem2.psc:OpenBlood`（行 356） | 低血位 ×2 → ApplyUtil(4) | 1 |
| 13 | 6 | `akCtl.ApplyUtil(4, 25.0 * akCtl.GetDamageMult(7) * akCtl.GLevel(6) * mult, 0, player)`；`src/ESSBReactions.psc:Open`（行 108） | ApplyUtil(4) | 1 |
| 14 | 0 | `ApplyUtil(6, 20.0 * GLevel(0) * ticks, 0, player)`；`src/ESSBController.psc:TickTimers`（行 4009） | ApplyUtil(6) | 1 |
| 15 | 1 | `akCtl.ApplyUtil(3, 25.0 * akCtl.GLevel(1), 0, akTarget)`；`src/ESSBElem.psc:OnFrozenTick`（行 513） | ApplyUtil(3) | 1 |
| 16 | 4 | `akCtl.ApplyUtil(6, 25.0 * akCtl.GLevel(4), 0, player)`；`src/ESSBElem2.psc:OnWindHit`（行 210） | ApplyUtil(6) | 1 |
| 17 | 8 | `ApplyUtil(4, 15.0 * GLevel(8) * ticks, 0, player)`；`src/ESSBController.psc:TickDomain`（行 4767） | 生命／耐力各自同一 G → ApplyUtil(4/6) | 1 |
| 18 | 6 | `akCtl.ApplyUtil(4, 2.0 * rank * akCtl.GLevel(6), 0, player)`；`src/ESSBElem2.psc:OpenDivine`（行 386） | ApplyUtil(4) | 1 |
| 19 | current | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, aiElement) * 3.0 * akCtl.GLevel(TreeOf(akCtl.CurrentElement.GetValueInt())), 0, player)`；`src/ESSBNodes.psc:OnEndReward`（行 248） | ApplyUtil(5)；TreeOf(CurrentElement)，非 common 的 12 | 1 |
| 20 | 3 | `Float drain = 3.0 * ESSBNodes.Rank(akCtl, 3, 0, 2) * akCtl.GLevel(3)`；`src/ESSBElem2.psc:OnEarthHit`（行 178） | ApplyUtil(3)；回耐另取同一未分類 drain ×0.5 | 1 |
| 21 | 10 | `akCtl.ApplyUtil(19, 25.0 * aiLayers * akCtl.GLevel(10), 10, player)`；`src/ESSBElem3.psc:OnAstralDetonate`（行 857） | ApplyUtil(19) | 1 |
| 22 | 10 | `akCtl.ApplyUtil(4, 20.0 * aiLayers * akCtl.GLevel(10), 0, player)`；`src/ESSBElem3.psc:OnAstralDetonate`（行 861） | ApplyUtil(4) | 1 |
| 23 | 5 | `ApplyUtil(4, 20.0 * GLevel(5) * ticks, 0, player)`；`src/ESSBController.psc:TickDomain`（行 4762） | ApplyUtil(4) | 1 |
| 24 | 9 | `Float gain = 30.0 * akCtl.GetDamageMult(10) * akCtl.GLevel(9)`；`src/ESSBElem3.psc:AfterDeathCurse`（行 653） | ApplyUtil(4/5) 各一次，不回寫 gain | 1 |
| 25 | 6 | `akCtl.ApplyUtil(4, afHealBase * akCtl.GetDamageMult(7) * akCtl.GLevel(6), 0, player)`；`src/ESSBElem2.psc:Judge`（行 720） | JudgeArea 分配 100 基準預算 → Judge → ApplyUtil(4) | 1 |
| 26 | 6 | `HealAllies(akCtl, 25.0 * akCtl.GLevel(6))`；`src/ESSBElem2.psc:OnDivineHit`（行 254） | HealAllies → ApplyUtil(4)；helper 不乘 G | 1 |
| 27 | 6 | `HealAllies(akCtl, 40.0 * akCtl.GLevel(6))`；`src/ESSBElem2.psc:OpenDivine`（行 402） | HealAllies → ApplyUtil(4) | 1 |
| 28 | 6 | `akCtl.ApplyUtil(4, 40.0 * akCtl.GLevel(6), 0, player)`；`src/ESSBElem2.psc:OpenDivine`（行 406） | ApplyUtil(4) | 1 |
| 29 | 6 | `ApplyUtil(4, 25.0 * GLevel(6) * ticks, 0, player)`；`src/ESSBController.psc:TickDomain`（行 4764） | 生命 25G／魔力 20G → ApplyUtil(4/5) | 1 |
| 30 | 6 | `ApplyUtil(5, 20.0 * GLevel(6) * ticks, 0, player)`；`src/ESSBController.psc:TickDomain`（行 4765） | 同 29 的 TickDomain；不重複領域回復 | 1 |
| 31 | 6 | `akCtl.ApplyUtil(4, 25.0 * akCtl.GetDamageMult(7) * akCtl.GLevel(6), 0, player)`；`src/ESSBElem2.psc:EndDivineNodes`（行 880） | ApplyUtil(4) | 1 |
| 32 | 11 | `akCtl.ApplyUtil(6, 60.0 * akCtl.GLevel(11), 0, player)`；`src/ESSBNoForm.psc:OnCombo`（行 101） | ApplyUtil(6) | 1 |
| 33 | 10 | `akCtl.ApplyUtil(5, 25.0 * akCtl.GLevel(10), 0, player)`；`src/ESSBElem3.psc:OnAstralHit`（行 303） | ApplyUtil(5) | 1 |
| 34 | 10 | `akCtl.ApplyUtil(5, 40.0 * akCtl.GLevel(10), 0, player)`；`src/ESSBElem3.psc:OpenAstral`（行 430） | ApplyUtil(5) | 1 |
| 35 | 9 | `Float drain = 40.0 * akCtl.GetDamageMult(10) * akCtl.GLevel(9) * mult`；`src/ESSBReactions.psc:Open`（行 121） | ApplyUtil(2/5) 各一次 | 1 |
| 36 | 9 | `Float drain = 30.0 * akCtl.GetDamageMult(10) * akCtl.GLevel(9)`；`src/ESSBElem3.psc:OnDarkHit`（行 259） | ApplyUtil(2/5) 各一次 | 1 |
| 37 | 9 | `akCtl.ApplyUtil(5, 15.0 * curse * akCtl.GLevel(9), 0, player)`；`src/ESSBElem3.psc:OnKill`（行 1189） | ApplyUtil(5) | 1 |
| 38 | 9 | `Float drain = 40.0 * akCtl.GetDamageMult(10) * akCtl.GLevel(9)`；`src/ESSBElem3.psc:OnAnyEnd`（行 1054） | ApplyUtil(2/5) 各一次 | 1 |
| 39 | 3 | `akCtl.ApplyUtil(3, 40.0 * akCtl.GLevel(3) * mult, 0, akTarget)`；`src/ESSBReactions.psc:Open`（行 92） | ApplyUtil(3) | 1 |
| 40 | 3 | `akCtl.ApplyUtil(6, 40.0 * akCtl.GLevel(3) * mult, 0, player)`；`src/ESSBReactions.psc:Open`（行 93） | ApplyUtil(6) | 1 |
| 41 | 4 | `akCtl.ApplyUtil(6, 40.0 * akCtl.GLevel(4), 0, player)`；`src/ESSBElem2.psc:OpenWind`（行 329） | ApplyUtil(6) | 1 |
| 42 | current | `Float amount = ESSBReactions.BaseMax(akCtl, akCtl.CurrentElement.GetValueInt()) * 4.0 * akCtl.GLevel(TreeOf(akCtl.CurrentElement.GetValueInt()))`；`src/ESSBNodes.psc:OnSyncStage`（行 120） | amount → ApplyUtil(4/5)；用當前元素樹 | 1 |
| 43 | 8 | `Float amount = ESSBReactions.ReactDamage(akCtl, 9, 2.0) * afMult * akCtl.GLevel(8)`；`src/ESSBElem3.psc:EndWaterNodes`（行 996） | ReactDamage 不乘 G；ApplyUtil(4/6)，不走 ApplyDamage | 1 |
| 44 | 0 | `akCtl.ApplyUtil(6, 50.0 * akCtl.GLevel(0), 0, player)`；`src/ESSBElem.psc:OpenFire`（行 248） | ApplyUtil(6) | 1 |
| 45 | 6 | `akCtl.ApplyUtil(4, 60.0 * akCtl.GLevel(6), 0, player)`；`src/ESSBElem2.psc:OnFormOpened`（行 468） | 玩家 ApplyUtil(4)；同伴 HealAllies → ApplyUtil(4) | 1 |
| 46 | 0 | `akCtl.ApplyUtil(4, 60.0 * akCtl.GLevel(0), 0, player)`；`src/ESSBElem.psc:OnIgnite`（行 404） | ApplyUtil(4) | 1 |
| 47 | 9 | `akCtl.ApplyUtil(5, 50.0 * akCtl.GLevel(9), 0, player)`；`src/ESSBElem3.psc:OnShadowBody`（行 1249） | ApplyUtil(5) | 1 |
| 48 | 6 | `akCtl.ApplyUtil(5, 60.0 * akCtl.GLevel(6), 0, player)`；`src/ESSBElem2.psc:OnAsh`（行 1043） | ApplyUtil(5) | 1 |
| 49 | 2 | `akCtl.ApplyUtil(2, 60.0 * akCtl.GetDamageMult(3) * akCtl.GLevel(2) * mult, 0, akTarget)`；`src/ESSBReactions.psc:Open`（行 87） | ApplyUtil(2) | 1 |
| 50 | 2 | `Ctl.ApplyUtil(2, 50.0 * Ctl.GetDamageMult(3) * Ctl.GLevel(2), 0, attacker)`；`src/ESSBGuard.psc:OnHitEx`（行 196） | ApplyUtil(2) | 1 |
| 51 | 2 | `akCtl.ApplyUtil(5, 60.0 * akCtl.GLevel(2), 0, player)`；`src/ESSBElem.psc:OpenShock`（行 305） | ApplyUtil(5) | 1 |
| 52 | 3 | `Return 4.0 * (1.0 + 0.03 * ESSBNodes.Rank(akCtl, 3, 2, 2)) * akCtl.GLevel(3)`；`src/ESSBElem2.psc:QuakeStamina`（行 494） | QuakeStamina → Quake.stamina → QuakeOne → ApplyUtil(3)；傷害 amount 另一支才進 ApplyDamage | 1 |
| 53 | 3 | `Return (60.0 + 4.0 * ESSBNodes.Rank(akCtl, 3, 0, 0)) * akCtl.GLevel(3)`；`src/ESSBElem2.psc:FissureArmor`（行 416） | FissureArmor → Open/OpenEarth → ApplyUtil(1)；擴散不乘開印 M | 1 |
| 54 | 3 | `Return 20.0 * akCtl.GLevel(3)`；`src/ESSBElem2.psc:RockArmorPerLayer`（行 31） | RockArmorPerLayer → SyncRockArmor → ApplyUtil(18) | 1 |
| 55 | 2 | `akCtl.ApplyUtil(2, amount * drainRatio * akCtl.GLevel(2), 0, akTarget)`；`src/ESSBElem.psc:Discharge`（行 539） | 直擊／跳躍 ApplyUtil(2) 各乘一次；amount 本身未乘 G，生命傷害另走 ApplyDamage | 1 |
| 56 | 3 | `akCtl.ApplyUtil(3, 80.0 * akCtl.GLevel(3), 0, akTarget)`；`src/ESSBElem2.psc:OnEarthHit`（行 191） | ApplyUtil(3) | 1 |
| 57 | 3 | `Return 25.0 * akCtl.GLevel(3)`；`src/ESSBElem2.psc:RockArmorPerLayer`（行 29） | RockArmorPerLayer → SyncRockArmor → ApplyUtil(18) | 1 |
| 58 | 2 | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 3) * charge * akCtl.GLevel(2), 0, player)`；`src/ESSBElem.psc:OnTick`（行 779） | ApplyUtil(5)；Discharge 不修改呼叫端 charge | 1 |
| 59 | 豁免 | `Return 1`；`src/ESSBElem3.psc:AstralDelay`（行 832） | AstralDelay；固定桶引爆延遲，G／Duration 豁免 | 0 |
| 60 | 豁免 | `player.RestoreActorValue("Health", 1.0 - player.GetActorValue("Health"))`；`src/ESSBController.psc:RefreshDivineProtection`（行 7548） | 神佑保命 1 HP，G／Recovery 豁免 | 0 |

既有已乘 G 的破魔、反噬及生命傷害不再加第二次；破魔在 `OnManaBreak` 先算 G、再 `DrainAmount`、再限制可吸取魔力，`ApplyUtil(2, ..., True)` 跳過重乘，真傷沿用 `abLevelScaled=True`。百分比治療長流、血盾 20% 上限、抗性百分點不新增 G。

### 分類倍率與施放位置

| 分類／GLOB（FormID） | 唯一倍率位置 | 覆蓋呼叫端／例外 |
|---|---|---|
| 傷害／ESSB_BaseDamageMult（00515A；沿用） | ApplyProc、ApplyDamage、ApplyTrueDamage、ApplyUtil(7) | 各為互斥施放終點；ApplyDamageRaw 不增乘。既有元素直傷、真傷與放血；自損／施放代價／Execute 不作可調傷害。 |
| 持續傷害／ESSB_MultDot（005168） | ApplyDotDamage；ApplyUtil(7)；EndBlood 的 remaining 項 | Status.Tick 毒／催毒／流血；放血生命比例；TickDomain 死域；血潮只乘剩餘流血、不乘即時生命百分比。 |
| 冷卻／ESSB_MultCooldown（005169） | CooldownSeconds | OpenMark、OpenSecond、TakeEndSlot、TakeInterrupt、TakeIceHeart、TakeRetaliate、TakeSanctuary、TakeCleanse、TakePush、Guard.TakeAttacker、雷雨充能、AvatarCooldown、毒擴散、Trees.RespecReady。洗點以 86400 秒換回遊戲日。 |
| 回復／ESSB_MultRecovery（00516A） | ApplyUtil(4/5/6/10/11/18/19/25)；Leech→RecoveryAmount（下游 True）；RefreshRecovery；ApplyInherit | 全部玩家／同伴生命魔耐、長流、聖域、血池、潮池；岩甲／血盾／星盾；冰盾／電盾／水鏡／聖盾 PERK 強度；溫血／感應／星輝回復率；血承生命／護甲盾。神佑 1 HP 明確跳過。血盾在乘回復後套原 20% cap。 |
| 削減／ESSB_MultDrain（00516B） | ApplyUtil(1/2/3)；OnManaBreak→DrainAmount（下游 True） | 裂痕護甲、感電、放電、深寒、地震、震擊、破魔、蝕魔／暗開印／蝕魔終焉。QuakeOne 判定讀 DrainAmount 以與實際削耐一致；不另乘到 damage 或汲力。抗性百分點與沉默鎖零不變。 |
| 持續時間／ESSB_MultDuration（00516C） | DurationSeconds／DurationInt | ApplyMark 同時設定法術與 registry；ApplyUtil 的狀態 duration；ApplyManaBreakMark／ApplySilenceSpell／Fear／Frenzy／Reanimate／Inherit；StartDomain；保留副印記；自身狀態 setter；Status 的 Frozen、Catalyze、DeathCurse、Airborne、StarLock setter 與熱度／凍結／裂痕／失衡／聖印／浸濕／水壓／詛咒到期比較。pending 存原秒數、ImportState 不再縮放。 |

平衡頁所有 slider 均為 0.25–3.0、step 0.05；冷卻 max=2.0。節點倍率預設沿用 3.0，傷害預設沿用 1.0，五個新增倍率預設 1.0。EDID 不新增 ESSB_MultDamage，避免重複傷害控制與 FormID 改名。

驗證證據：`build/fix7-build.log`、`build/fix7-check.json`、`build/fix7-g-proof.json`、`build/fix5-mcm-check.json`、`build/v03-compile-results.json`。建置內繼續執行原 DOT、LAYOUT、FIX3、FIX4、MCM、FIX6、READBACK、PLAN、CSF、DELIVERY、PLAN COVERAGE、NODE INDEX、FX 與 ENGINE COVERAGE 檢查；新增 FIX7 檢查 5 GLOB 的型別／預設／VMAD、3907 舊 FormID、不同倍率的實際 utility 公式、裁決 1–6 目標上限、G 來源、固定匯出和編碼。

檔案編碼／換行：修改的來源沿用 UTF-8（無 BOM）及各檔原 LF／CRLF；`實作紀錄.md` 只在原始位元組尾部追加，原文未重寫。產物位於 `package/Elements Spellblade`，沒有安裝到 MO2 或遊戲。
