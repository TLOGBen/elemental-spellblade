

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
| 02 | 命中流血目標吸血（固定 B 基準） | B_max 10 × 吸血比 × 血位命中倍率；基礎滿血 0.65，低血 3；吸血主線滿點滿血 2.6、低血 3.9 | B_max ×5 × 原吸血比 × 血位命中倍率 | `native/include/HitMath.h:AddBloodLeech`（行 387） |
| 03 | 切換受傷 -50% 視窗 | 1 秒 | 2 秒 | `src/ESSBController.psc:SwitchForm`（行 1384） |
| 04 | 斷咒附帶沉默 | 1 秒（每 5 秒至多一次） | 1 秒（保留） | `src/ESSBNoForm.psc:OnInterruptCast`（行 46） |
| 05 | 低點數沉默及首領折半 | 1+0.2×rank，四捨五入；rank1–2 實際 1 秒，首領最少1秒 | 1+0.2×rank，原四捨五入及首領折半（保留） | `native/include/HitMath.h:SilenceSeconds`（行 558） |
| 06 | B_max 固定基準命中回血 | 10 × 0.02 × rank，滿點 3／擊 | 1 × rank | `src/ESSBElem2.psc:OnDivineHit（round 21 已移除）`（行 0） |
| 07 | 風刃命中回耐 | 3／次 | 15／次 | `src/ESSBElem2.psc:WindBladeOne`（行 532） |
| 08 | 融斷每個印記回魔 | B_max ×0.5；依元素 = 3.5–12.5／印記 | B_max ×2／印記 | `src/ESSBNoForm.psc:OnBurst`（行 142） |
| 09 | 附近每名中毒敵人每秒回血 | 4.5／人／秒，最多 5 人 = 22.5 | 6／人／秒，最多 5 人 | `src/ESSBElem3.psc:PoisonFormTick`（行 788） |
| 10 | 開印回血 | B_max 9 × 0.5 = 4.5 | 25 | `src/ESSBElem3.psc:OpenPoison`（行 262） |
| 11 | 命中削耐的一半回耐 | 0.25 × rank，滿點 3.75／擊 | 1.5 × rank | `native/include/HitMath.h:AddFlatHitNodes`（行 415） |
| 12 | 開印固定回血 | 10 × 0.5 = 5；低血位 ×2 = 10 | 25，低血位 50 | `src/ESSBElem2.psc:OpenBlood`（行 291） |
| 13 | 聖印開印基礎回血 | B_max 10 ×0.5 ×環境 M ×開印 M；無分支滿點白天 8.7、夜晚 7.25 | 25 × 環境 M × 開印 M | `src/ESSBReactions.psc:Open`（行 108） |
| 14 | 熔身每秒回耐 | 5／秒 ×10 秒 = 50 | 20／秒 | `src/ESSBController.psc:TickTimers`（行 4031） |
| 15 | 冰封期間每秒削耐 | 5／秒 | 25／秒 | `src/ESSBElem.psc:OnFrozenTick`（行 468） |
| 16 | 命中回耐 | 5／擊 | 25／擊 | `native/include/HitMath.h:AddFlatHitNodes`（行 424） |
| 17 | 水域每秒回生命與耐力 | 各 B_max = 7／秒，5 秒各 35 | 生命與耐力各 15／秒 | `src/ESSBController.psc:TickDomain`（行 4773） |
| 18 | 開印額外回血 | 10 × 0.05 × rank，滿點 7.5 | 2 × rank | `src/ESSBElem2.psc:OpenDivine`（行 321） |
| 19 | 每次終焉回魔 | B_max；依元素 = 7–25 | B_max ×3 | `src/ESSBNodes.psc:OnEndReward`（行 223） |
| 20 | 每擊固定削耐 | 0.5 × rank；滿點 7.5 | 3 × rank | `native/include/HitMath.h:AddFlatHitNodes`（行 415） |
| 21 | 引爆臨時生命護盾 | B_max 10 ×當次引爆層數，10 秒；同款 Peak Value Modifier 不逐次相加 | 25／引爆層 | `src/ESSBElem3.psc:OnAstralDetonate（round 21 已移除）`（行 0） |
| 22 | 星痕引爆回血 | B_max 10 ×當次層數 | 20／引爆層 | `src/ESSBElem3.psc:OnAstralDetonate（round 21 已移除）`（行 0） |
| 23 | 血池每秒回血 | B_max 10／秒，5 秒共 50 | 20／秒 | `src/ESSBController.psc:TickDomain`（行 4767） |
| 24 | 死咒結算吸血與吸魔 | 各 10 ×環境 M（夜晚 12） | 生命與魔力各 30 × 環境 M | `src/ESSBElem3.psc:AfterDeathCurse`（行 532） |
| 25 | 裁決回血（每名被裁決目標各一次） | B_max 10 ×環境 M，白天 12／次；範圍最多 6 次 = 72 | 25／目標，單次累計 min(25×目標數,100)，再乘環境 M | `src/ESSBElem2.psc:Judge`（行 649） |
| 26 | 命中治療每名同伴 | B_max 10／擊 | 25／同伴／擊 | `src/ESSBElem2.psc:OnDivineHit（round 21 已移除）`（行 0） |
| 27 | 開印治療每名同伴 | B_max 10 | 40／同伴 | `src/ESSBElem2.psc:OpenDivine`（行 333） |
| 28 | 聖引預約下一開印治療玩家 | B_max 10 | 40 | `src/ESSBElem2.psc:OpenDivine`（行 337） |
| 29 | 聖域每秒回生命與魔力 | 各 B_max 10／秒，5 秒各 50 | 生命 25／秒、魔力 20／秒 | `src/ESSBController.psc:TickDomain`（行 4769） |
| 30 | 神聖領域同一回復路徑，延長時長 | 各 10／秒，8 秒各 80 | 同 29；同一領域，不另疊加 | `src/ESSBController.psc:TickDomain`（行 4770） |
| 31 | 聖印記融斷每目標額外治療 | 10 ×環境 M，白天 12 | 25 × 環境 M／目標 | `src/ESSBElem2.psc:EndDivineNodes`（行 778） |
| 32 | 連續三次命中回耐 | 25／三擊 | 60／三擊 | `src/ESSBNoForm.psc:OnCombo（round 21 已移除）`（行 0） |
| 33 | 命中回魔 | B_max 10 | 25 | `src/ESSBElem3.psc:OnAstralHit（round 21 已移除）`（行 0） |
| 34 | 開印回魔 | B_max 10 | 40 | `src/ESSBElem3.psc:OpenAstral（round 21 已移除）`（行 0） |
| 35 | 詛咒開印吸魔／回魔 | 10 ×環境 M ×開印 M；滿點夜晚 17.4 | 40 × 原倍率 | `src/ESSBReactions.psc:Open`（行 121） |
| 36 | 命中詛咒目標吸魔／回魔 | B_max 10 ×環境 M，夜晚 12 | 30 × 環境 M | `src/ESSBElem3.psc:OnDarkHit（round 21 已移除）`（行 0） |
| 37 | 詛咒目標死亡回魔 | B_max 10 ×詛咒層數，1–13 層 = 10–130 | 15／詛咒層 | `src/ESSBElem3.psc:OnKill（round 21 已移除）`（行 0） |
| 38 | 蝕魔終焉預約下一終焉吸魔／回魔 | 10 ×環境 M（夜晚 12） | 40 × 環境 M | `src/ESSBElem3.psc:OnAnyEnd（round 21 已移除）`（行 0） |
| 39 | 裂痕開印削耐 | 10 × 開印倍率（滿點 14.5） | 40 × 開印倍率 | `src/ESSBReactions.psc:Open`（行 92） |
| 40 | 裂痕開印回耐 | 10 | 40 | `src/ESSBReactions.psc:Open`（行 93） |
| 41 | 開印回耐 | 10 | 40 | `src/ESSBElem2.psc:OpenWind`（行 264） |
| 42 | 同調升段回生命與魔力 | 各 B_max ×2；依元素 = 14–50 | 生命與魔力各 B_max ×4 | `src/ESSBNodes.psc:OnSyncStage`（行 104） |
| 43 | 水印記融斷治療與回耐 | 各 B_max 7 ×2 ×afMult；倍率中含新通用／元素／無形態融斷節點 | 各 B_max ×2 ×afMult（保留基準 14） | `src/ESSBElem3.psc:EndWaterNodes`（行 721） |
| 44 | 開印回耐 | 15 | 50 | `src/ESSBElem.psc:OpenFire`（行 234） |
| 45 | 聖臨時玩家與附近同伴回血 | 各 B_max 10 ×2 = 20 | 玩家與同伴各 60 | `src/ESSBElem2.psc:OnFormOpened`（行 399） |
| 46 | 自燃回血 | B_max 12 ×2 = 24 | 60 | `src/ESSBElem.psc:OnIgnite（round 21 已移除）`（行 0） |
| 47 | 影身觸發回魔 | B_max 10 ×2 = 20 | 50 | `src/ESSBElem3.psc:OnShadowBody（round 21 已移除）`（行 0） |
| 48 | 化灰回魔 | B_max 10 ×2 = 20 | 60 | `src/ESSBElem2.psc:OnAsh`（行 887） |
| 49 | 感電開印削魔 | B_max 25 ×開印倍率，滿點 36.25 | 60 × 開印倍率 | `src/ESSBReactions.psc:Open`（行 87） |
| 50 | 被近戰命中時感電削魔 | B_max 25 | 50 | `src/ESSBGuard.psc:OnHitEx（round 21 已移除）`（行 0） |
| 51 | 開印回魔 | B_max 25 | 60 | `src/ESSBElem.psc:OpenShock`（行 286） |
| 52 | 地震削耐基準及主線 | B_max 10 ×2 ×(1+0.03×rank) ×終焉 M；rank15 基準29 | 40 ×(1+0.03×rank) ×終焉 M | `src/ESSBElem2.psc:QuakeStamina`（行 426） |
| 53 | 裂痕削甲（主線追加） | 30 +2 ×rank；滿點 60，再乘開印 M；擴散目標不乘開印 M | 60+4×rank | `src/ESSBElem2.psc:FissureArmor`（行 345） |
| 54 | 每層岩甲護甲 | 15／層；基礎 5 層 = 75；萬象後 8 層 =120 | 20／層 | `src/ESSBElem2.psc:RockArmorPerLayer`（行 29） |
| 55 | 放電削魔及跳躍削魔 | 傷害未乘 G 的 amount ×0.5（電蝕 1.0）；跳躍再 ×0.4（電弧 0.8）；B_max=25 | amount ×原削魔比；跳躍仍 ×原跳躍比（保留） | `src/ESSBElem.psc:Discharge`（行 491） |
| 56 | 重擊消耗裂痕額外削耐 | 50 | 80 | `src/ESSBElem2.psc:OnEarthHit`（行 160） |
| 57 | 磐石每層岩甲護甲 | 25／層；厚土＋萬象最多 13 層 =325 | 25／層（保留） | `src/ESSBElem2.psc:RockArmorPerLayer`（行 31） |
| 58 | 滿電荷自動放電回魔 | B_max 25 ×charge；基礎 cap6=150；主線＋萬象 cap14=350 | B_max ×charge（保留） | `src/ESSBElem.psc:OnTick`（行 722） |
| 59 | 高點數星痕引爆延遲 | rank≥10 時 1 秒；否則2秒 | rank≥10 為 1 秒，否則 2 秒（保留） | `src/ESSBElem3.psc:AstralDelay`（行 615） |
| 60 | 神佑救命瞬間回血 | 1 HP，另給2秒守護 | 1 HP（保留） | `src/ESSBController.psc:RefreshDivineProtection`（行 7531） |

### G(L) 單次縮放證據

`ESSBTrees.TreeG`＝`1.0 + 0.05 * TreeLevel(aiTree)`。下表列實際可 grep 的來源行與完整 utility 下游；`BaseMax`、`ReactDamage`、`HealAllies`、`Leech`、`ApplyUtil` 均不新增 G。回復／削減分類倍率只處理金額，不回寫 caller 的局部變數。傷害側 `ApplyDamage` 仍只在原 choke point 乘 G；放電的 utility 分支另乘，未提前污染共用 damage amount。

| ID | 所屬樹 | 唯一 G 來源（原碼） | 下游路徑 | G 次數 |
|---|---|---|---|---|
| 01 | 豁免 | `akCtl.Leech(50.0 * akCtl.GetBloodLeechRatio() * mult)   ; v0.4 沒寫量也沒寫 G(L)：沿用 50、拿掉 G`；`src/ESSBReactions.psc:Open`（行 103） | round 21 審查修正（裁定 C1）：2.x 血痕開印：依血位吸血，v0.4 沒寫量也沒寫 G（審查修正）；不乘 G(L) | 0 |
| 02 | 5 | `const float heal = procMagnitude * LeechRatio(p, nodes) * t.multRecovery;`；`native/include/HitMath.h:AddBloodLeech`（行 387） | Cast::kHeal / kBloodGuard；G 在附傷強度（RollProc）裡乘過一次 | 1 |
| 03 | 豁免 | `SetGuardSwitch(1)`；`src/ESSBController.psc:SwitchForm`（行 1384） | round 21 審查修正（裁定 C1）：5.2 順轉：切換後 1 秒；不乘 G(L) | 0 |
| 04 | 豁免 | `akTarget.InterruptCast()`；`src/ESSBNoForm.psc:OnInterruptCast`（行 46） | round 21 審查修正（裁定 C1）：5.1 斷咒：打斷施法（不是沉默）；不乘 G(L) | 0 |
| 05 | 豁免 | `const float wanted = std::min(1.0f + 0.2f * static_cast<float>(nodes.Rank(node::kNoFormSilence)), static_cast<float>(kMaxSilenceSeconds));`；`native/include/HitMath.h:SilenceSeconds`（行 558） | Cast::kSilence（固定時長法術）；G 豁免 | 0 |
| 06 | 6 | `—`；`src/ESSBElem2.psc:OnDivineHit（round 21 已移除）`（行 0） | 聖 命中回血主線：v0.4 主線換成別的效果（ESSBElem2.OnDivineHit 只留護持） | 0 |
| 07 | 豁免 | `akCtl.ApplyUtil(6, 3.0, 0, player)`；`src/ESSBElem2.psc:WindBladeOne`（行 532） | round 21 審查修正（裁定 C1）：5.7 追風：回耐力 3；不乘 G(L) | 0 |
| 08 | 豁免 | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, aiElement) * 0.5 * aiMarks, 0, player)`；`src/ESSBNoForm.psc:OnBurst`（行 142） | round 21 審查修正（裁定 C1）：5.1 回流：每個印記 B_max ×0.5；不乘 G(L) | 0 |
| 09 | 豁免 | `heal = heal + 6.0`；`src/ESSBElem3.psc:PoisonFormTick`（行 788） | round 21 審查修正（裁定 C1）：5.10 百毒不侵：v0.4 沒寫量，沿用 6、不乘 G；不乘 G(L) | 0 |
| 10 | 豁免 | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 8) * 0.5, 0, player)`；`src/ESSBElem3.psc:OpenPoison`（行 262） | round 21 審查修正（裁定 C1）：5.10 毒血：B_max ×0.5；不乘 G(L) | 0 |
| 11 | 3 | `const float cut = 3.0f * static_cast<float>(nodes.Rank(node::kEarthStaminaCut)) * TreeG(t, TreeOf(kEarth));`；`native/include/HitMath.h:AddFlatHitNodes`（行 415） | Cast::kDrainStamina；回耐 ×0.5 另一步 | 1 |
| 12 | 豁免 | `Float heal = ESSBReactions.BaseMax(akCtl, 6) * 0.5`；`src/ESSBElem2.psc:OpenBlood`（行 291） | round 21 審查修正（裁定 C1）：5.8 開印回血：B_max ×0.5；不乘 G(L) | 0 |
| 13 | 豁免 | `akCtl.ApplyUtil(4, BaseMax(akCtl, 7) * 0.5 * mult, 0, player)`；`src/ESSBReactions.psc:Open`（行 108） | round 21 審查修正（裁定 C1）：2.x 聖印開印：回血 B_max ×0.5；不乘 G(L) | 0 |
| 14 | 豁免 | `ApplyUtil(6, 5.0 * ticks, 0, player)`；`src/ESSBController.psc:TickTimers`（行 4031） | round 21 審查修正（裁定 C1）：5.3 熔身：每秒回耐力 5；不乘 G(L) | 0 |
| 15 | 豁免 | `akCtl.ApplyUtil(21, 100.0, 2, akTarget)`；`src/ESSBElem.psc:OnFrozenTick`（行 468） | round 21 審查修正（裁定 C1）：5.4 深寒：耐力不回復（不是主動削耐）；不乘 G(L) | 0 |
| 16 | 4 | `plan.Add({ Cast::kRestoreStamina, 25.0f * TreeG(t, TreeOf(kWind)) * t.multRecovery });`；`native/include/HitMath.h:AddFlatHitNodes`（行 424） | Cast::kRestoreStamina | 1 |
| 17 | 豁免 | `ApplyUtil(4, 15.0 * ticks, 0, player)`；`src/ESSBController.psc:TickDomain`（行 4773） | round 21 審查修正（裁定 C1）：5.11 潮池：v0.4 沒寫量，不乘 G；不乘 G(L) | 0 |
| 18 | 豁免 | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 7) * 0.05 * rank, 0, player)`；`src/ESSBElem2.psc:OpenDivine`（行 321） | round 21 審查修正（裁定 C1）：5.9 開印回血 +5%／點（B_max 為基準）；不乘 G(L) | 0 |
| 19 | 豁免 | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, aiElement), 0, player)`；`src/ESSBNodes.psc:OnEndReward`（行 223） | round 21 審查修正（裁定 C1）：5.2 反哺：B_max 魔力；不乘 G(L) | 0 |
| 20 | 3 | `const float cut = 3.0f * static_cast<float>(nodes.Rank(node::kEarthStaminaCut)) * TreeG(t, TreeOf(kEarth));`；`native/include/HitMath.h:AddFlatHitNodes`（行 415） | Cast::kDrainStamina；Cast::kRestoreStamina 取同一 cut ×0.5 | 1 |
| 21 | 10 | `—`；`src/ESSBElem3.psc:OnAstralDetonate（round 21 已移除）`（行 0） | 星 引爆（OnAstralDetonate）：v0.4 星樹改版，星爆連鎖屬 N5 | 0 |
| 22 | 10 | `—`；`src/ESSBElem3.psc:OnAstralDetonate（round 21 已移除）`（行 0） | 星 引爆（OnAstralDetonate）：同 21 | 0 |
| 23 | 豁免 | `ApplyUtil(4, 20.0 * ticks, 0, player)`；`src/ESSBController.psc:TickDomain`（行 4767） | round 21 審查修正（裁定 C1）：5.8 血池：v0.4 沒寫量，不乘 G；不乘 G(L) | 0 |
| 24 | 豁免 | `Float gain = ESSBReactions.BaseMax(akCtl, 10)`；`src/ESSBElem3.psc:AfterDeathCurse`（行 532） | round 21 審查修正（裁定 C1）：5.12 饕餮：各 B_max ×1.0；不乘 G(L) | 0 |
| 25 | 豁免 | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 7), 0, player)`；`src/ESSBElem2.psc:Judge`（行 649） | round 21 審查修正（裁定 C1）：2.x 裁決：治療你 B_max ×1.0（round 7 的累計預算不在 v0.4）；不乘 G(L) | 0 |
| 26 | 6 | `—`；`src/ESSBElem2.psc:OnDivineHit（round 21 已移除）`（行 0） | 聖 祝福（HealAllies）：v0.4 移除 | 0 |
| 27 | 豁免 | `HealAllies(akCtl, ESSBReactions.BaseMax(akCtl, 7))`；`src/ESSBElem2.psc:OpenDivine`（行 333） | round 21 審查修正（裁定 C1）：5.9 聖光：同伴回血 B_max；不乘 G(L) | 0 |
| 28 | 豁免 | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 7), 0, player)`；`src/ESSBElem2.psc:OpenDivine`（行 337） | round 21 審查修正（裁定 C1）：5.9 聖引：治療你 B_max；不乘 G(L) | 0 |
| 29 | 豁免 | `ApplyUtil(4, 25.0 * ticks, 0, player)`；`src/ESSBController.psc:TickDomain`（行 4769） | round 21 審查修正（裁定 C1）：5.9 聖域：v0.4 沒寫量，不乘 G；不乘 G(L) | 0 |
| 30 | 豁免 | `ApplyUtil(5, 20.0 * ticks, 0, player)`；`src/ESSBController.psc:TickDomain`（行 4770） | round 21 審查修正（裁定 C1）：5.9 聖域：同上；不乘 G(L) | 0 |
| 31 | 豁免 | `akCtl.ApplyUtil(4, ESSBReactions.BaseMax(akCtl, 7), 0, player)`；`src/ESSBElem2.psc:EndDivineNodes`（行 778） | round 21 審查修正（裁定 C1）：5.9 聖斷：每個目標治療你 B_max ×1.0；不乘 G(L) | 0 |
| 32 | 11 | `—`；`src/ESSBNoForm.psc:OnCombo（round 21 已移除）`（行 0） | 純武藝 連擊（OnCombo）：v0.4 無形態樹改成吸魔／滅法，武藝線移除 | 0 |
| 33 | 10 | `—`；`src/ESSBElem3.psc:OnAstralHit（round 21 已移除）`（行 0） | 星 命中（OnAstralHit）星軌：v0.4 移除 | 0 |
| 34 | 10 | `—`；`src/ESSBElem3.psc:OpenAstral（round 21 已移除）`（行 0） | 星 開印 星光：v0.4 移除 | 0 |
| 35 | 豁免 | `Float drain = BaseMax(akCtl, 10) * mult`；`src/ESSBReactions.psc:Open`（行 121） | round 21 審查修正（裁定 C1）：2.x 詛咒開印：吸魔 B_max ×1.0；不乘 G(L) | 0 |
| 36 | 9 | `—`；`src/ESSBElem3.psc:OnDarkHit（round 21 已移除）`（行 0） | 暗 蝕魔（OnDarkHit）：v0.4 改名為奪魔並移到無形態樹（DLL） | 0 |
| 37 | 9 | `—`；`src/ESSBElem3.psc:OnKill（round 21 已移除）`（行 0） | 星 擊殺（OnKill）：v0.4 移除 | 0 |
| 38 | 9 | `—`；`src/ESSBElem3.psc:OnAnyEnd（round 21 已移除）`（行 0） | 星 任何終焉（OnAnyEnd）星界之門：v0.4 移除 | 0 |
| 39 | 豁免 | `akCtl.ApplyUtil(3, 10.0 * mult, 0, akTarget)`；`src/ESSBReactions.psc:Open`（行 92） | round 21 審查修正（裁定 C1）：2.x 裂痕開印：目標耐力 -10；不乘 G(L) | 0 |
| 40 | 豁免 | `akCtl.ApplyUtil(6, 10.0 * mult, 0, player)`；`src/ESSBReactions.psc:Open`（行 93） | round 21 審查修正（裁定 C1）：2.x 裂痕開印：你回復 10 耐力；不乘 G(L) | 0 |
| 41 | 豁免 | `akCtl.ApplyUtil(6, 10.0, 0, player)`；`src/ESSBElem2.psc:OpenWind`（行 264） | round 21 審查修正（裁定 C1）：5.7 氣流：開印回 10 耐力；不乘 G(L) | 0 |
| 42 | 豁免 | `Float amount = ESSBReactions.BaseMax(akCtl, akCtl.CurrentElement.GetValueInt()) * 2.0`；`src/ESSBNodes.psc:OnSyncStage`（行 104） | round 21 審查修正（裁定 C1）：5.2 回饋：各 B_max ×2；不乘 G(L) | 0 |
| 43 | 8 | `Float amount = ESSBReactions.ReactDamage(akCtl, 9, 1.0) * afMult * akCtl.GLevel(8)`；`src/ESSBElem3.psc:EndWaterNodes`（行 721） | ReactDamage 不乘 G；ApplyUtil(4/6)，不走 ApplyDamage | 1 |
| 44 | 豁免 | `akCtl.ApplyUtil(6, 15.0, 0, player)`；`src/ESSBElem.psc:OpenFire`（行 234） | round 21 審查修正（裁定 C1）：5.3 餘熱：開印回 15 耐力；不乘 G(L) | 0 |
| 45 | 豁免 | `Float heal = ESSBReactions.BaseMax(akCtl, 7) * 2.0`；`src/ESSBElem2.psc:OnFormOpened`（行 399） | round 21 審查修正（裁定 C1）：5.9 聖臨強化：B_max ×2；不乘 G(L) | 0 |
| 46 | 0 | `—`；`src/ESSBElem.psc:OnIgnite（round 21 已移除）`（行 0） | 火 火浴（OnIgnite）：v0.4 改成 N3 的節點（只有 perk 記錄） | 0 |
| 47 | 9 | `—`；`src/ESSBElem3.psc:OnShadowBody（round 21 已移除）`（行 0） | 暗 影身（OnShadowBody）：v0.4 移除 | 0 |
| 48 | 豁免 | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 7) * 2.0, 0, player)`；`src/ESSBElem2.psc:OnAsh`（行 887） | round 21 審查修正（裁定 C1）：5.9 聖灰：回魔 B_max ×2；不乘 G(L) | 0 |
| 49 | 豁免 | `akCtl.ApplyUtil(2, BaseMax(akCtl, 3) * mult, 0, akTarget)`；`src/ESSBReactions.psc:Open`（行 87） | round 21 審查修正（裁定 C1）：2.x 感電開印：目標魔力 -B_max ×1.0；不乘 G(L) | 0 |
| 50 | 2 | `—`；`src/ESSBGuard.psc:OnHitEx（round 21 已移除）`（行 0） | 雷 靜電的削魔 50×G：v0.4 靜電只是「攻擊者感電」（掛雷印記），發明的削魔拿掉（審查修正） | 0 |
| 51 | 豁免 | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 3), 0, player)`；`src/ESSBElem.psc:OpenShock`（行 286） | round 21 審查修正（裁定 C1）：5.5 充能開印：B_max 魔力；不乘 G(L) | 0 |
| 52 | 3 | `Return 2.0 * (1.0 + 0.03 * ESSBNodes.Rank(akCtl, 3, 2, 2)) * akCtl.GLevel(3) ; @node 地震耐力削減`；`src/ESSBElem2.psc:QuakeStamina`（行 426） | QuakeStamina → Quake.stamina → QuakeOne → ApplyUtil(3)；傷害 amount 另一支才進 ApplyDamage | 1 |
| 53 | 豁免 | `Return 30.0 + 2.0 * ESSBNodes.Rank(akCtl, 3, 0, 0) ; @node 裂痕護甲削減`；`src/ESSBElem2.psc:FissureArmor`（行 345） | round 21 審查修正（裁定 C1）：5.6 裂痕護甲削減 -30 → -60（+2／點）；不乘 G(L) | 0 |
| 54 | 豁免 | `Return 40.0`；`src/ESSBElem2.psc:RockArmorPerLayer`（行 29） | round 21 審查修正（裁定 C1）：5.6 磐石：每層護甲 +40；不乘 G(L) | 0 |
| 55 | 2 | `akCtl.ApplyUtil(2, amount * drainRatio * akCtl.GLevel(2), 0, akTarget)`；`src/ESSBElem.psc:Discharge`（行 491） | 直擊／跳躍 ApplyUtil(2) 各乘一次；amount 本身未乘 G，生命傷害另走 ApplyDamage | 1 |
| 56 | 豁免 | `akCtl.ApplyUtil(3, 50.0, 0, akTarget)`；`src/ESSBElem2.psc:OnEarthHit`（行 160） | round 21 審查修正（裁定 C1）：5.6 震擊：削減 50 耐力；不乘 G(L) | 0 |
| 57 | 豁免 | `Return 25.0`；`src/ESSBElem2.psc:RockArmorPerLayer`（行 31） | round 21 審查修正（裁定 C1）：5.6 岩甲：每層護甲 +25；不乘 G(L) | 0 |
| 58 | 豁免 | `akCtl.ApplyUtil(5, ESSBReactions.BaseMax(akCtl, 3) * charge, 0, player)`；`src/ESSBElem.psc:OnTick`（行 722） | round 21 審查修正（裁定 C1）：5.5 雷神：v0.4 沒寫回魔量，不乘 G；不乘 G(L) | 0 |
| 59 | 豁免 | `Return 1`；`src/ESSBElem3.psc:AstralDelay`（行 615） | AstralDelay；固定桶引爆延遲，G／Duration 豁免 | 0 |
| 60 | 豁免 | `player.RestoreActorValue("Health", 1.0 - player.GetActorValue("Health"))`；`src/ESSBController.psc:RefreshDivineProtection`（行 7531） | 神佑保命 1 HP，G／Recovery 豁免 | 0 |

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
