# 技能樹 v0.4 重建盤點

盤點時間：2026-09-25 19:55（+08:00）。性質：唯讀盤點，只新增本檔，沒有改任何產品檔。

**讀的是哪一版**：`native/`、`src/`、`build_v03.py`、`build/*.py` 目前有另一個代理在做 round 20（N2），工作樹是改到一半的狀態（見 `git status`：`native/include/ManifestData.h`、`build/fix19_native.py`、`src/ESSBController.psc` 等都有未提交修改，另有未追蹤的 `native/include/NodeIds.h`、`HitMath.h`、`EngineFacts.h`、`build/fix20_*.py`）。本檔以**目前的工作樹**為準；凡是 N2 會改到的接線（DLL 讀哪些格、Papyrus 哪些預寫被拿掉），都可能在 round 20 收尾時再變，表內用「N2 正在接」標出來。

**資料來源**

| 用途 | 檔案 |
|---|---|
| v0.4 設計真相 | `元素魔戰士規劃-v0.4.md` 第 5 節（5.1～5.13 的「路線／階／節點／觸發／負責」表，另參考第 3 節與 5 節開頭的骨架表） |
| 現有節點（ESP 實際產生的） | `build/plan-tree-nodes.json`（`plan_trees.py` 從 **v0.3** 規劃解析出來，再經 `apply_balance_text`／`apply_fix8_decisions` 處理） |
| 現有 FormID | `build/v03-formids.json`（上一次建置寫出的 manifest） |
| 現有實作位置 | `plan_coverage.py` 的 `NODES`（每個 v0.3 節點都登記了「腳本:函式」或「PERK 進入點」） |
| Papyrus 讀取點 | `src/*.psc` 裡字面的 `Rank(樹, 路線, 階)`／`Br(樹, 路線, 階, n)`、`GetBranch`／`GetMainPerk`，以及用變數 `tree` 讀的共用骨架 |
| DLL 讀取點 | `native/include/ManifestData.h` 的 `namespace node`（由 `build/fix19_native.py` 產生）、`native/include/HitMath.h`、`native/include/EngineFacts.h`、`native/src/Plugin.cpp` |

**分類定義**

| 分類 | 意思 |
|---|---|
| SAME | 同一格、效果相同（v0.4 只是補充說明或改措辭，也算 SAME，備註會寫） |
| RETUNED | 同一格、機制相同，只改數字、改名，或因為基礎系統換單位（例如毒「層」→「劑」、火熱度「層」→「階」）而改寫法 |
| CHANGED | 同一格（主線，或同名分支），但機制換了 |
| NEW | 現有 ESP 沒有對應 perk |
| REMOVED | 現有 perk 在 v0.4 沒有對應（多半是改成基礎機制、或被設計刪掉） |

判定規則：主線每階固定一格，只會是 SAME／RETUNED／CHANGED。分支先按**名字**配對（同一階內）；名字不同但設計明顯是同一個節點改名的（血盾→血溢、蝕魔→奪魔、逆流→噬命、衰弱→萎靡、瘴氣→疫染、回流→湧泉、沖刷→開印沖刷）算 RETUNED；其餘沒配到的就是 NEW／REMOVED，**不硬把不同機制塞進同一格**。「現有效果」一欄用 v0.3 的基準值（`description_original`／`main_original`），遊戲內 DESC 顯示的是乘過 `node_percent_scale`（3）之後的數字；v0.4 表格也是基準值，兩邊可以直接比。

## 1. 總數

| 樹 | 章節 | 主線 SAME | 主線 RETUNED | 主線 CHANGED | 分支 SAME | 分支 RETUNED | 分支 CHANGED | 分支 NEW | 分支 REMOVED | 分支數 v0.3 → v0.4 |
|---|---|---|---|---|---|---|---|---|---|---|
| 無元素（`noform`） | 5.1 | 4 | 2 | 9 | 9 | 4 | 3 | 9 | 9 | 25 → 25 |
| 全元素通用（`common`） | 5.2 | 13 | 1 | 1 | 20 | 0 | 1 | 2 | 2 | 23 → 23 |
| 火焰（`fire`） | 5.3 | 10 | 1 | 4 | 6 | 7 | 10 | 1 | 1 | 24 → 24 |
| 冰霜（`frost`） | 5.4 | 14 | 1 | 0 | 9 | 8 | 4 | 3 | 2 | 23 → 24 |
| 雷電（`lightning`） | 5.5 | 15 | 0 | 0 | 16 | 2 | 2 | 2 | 2 | 22 → 22 |
| 大地（`earth`） | 5.6 | 15 | 0 | 0 | 12 | 3 | 6 | 1 | 0 | 21 → 22 |
| 風（`wind`） | 5.7 | 14 | 0 | 1 | 20 | 4 | 1 | 0 | 0 | 25 → 25 |
| 鮮血（`blood`） | 5.8 | 15 | 0 | 0 | 17 | 2 | 4 | 1 | 1 | 24 → 24 |
| 神聖（`divine`） | 5.9 | 13 | 0 | 2 | 12 | 4 | 6 | 3 | 3 | 25 → 25 |
| 毒素（`poison`） | 5.10 | 10 | 4 | 1 | 8 | 11 | 3 | 0 | 0 | 22 → 22 |
| 水（`water`） | 5.11 | 13 | 1 | 1 | 10 | 2 | 4 | 5 | 5 | 21 → 21 |
| 黑暗（`darkness`） | 5.12 | 14 | 0 | 1 | 8 | 0 | 4 | 12 | 12 | 24 → 24 |
| 星界（`astral`） | 5.13 | 11 | 1 | 3 | 6 | 2 | 1 | 8 | 12 | 21 → 17 |
| **合計** |  | **161** | **11** | **23** | **153** | **49** | **49** | **47** | **49** | **300 → 298** |

重點：

- 主線 195 格全部還在（13 × 3 × 5 沒變），161 格效果不變，23 格要換機制。換最兇的是**無元素**（15 條主線換掉 9 條，三條路線改名為大師／滅法／冷寂）、**火**（熱度搬到玩家身上）、**星**（改成共鳴／闇星）、**神聖**（改成玩家側聖佑）。
- 分支 300 → 298：沿用 251 個（其中 49 個機制換掉），新增 47 個，移除 49 個。**黑暗**（新舊各換 12 個）和**星**（移除 12、新增 8）幾乎是重做。
- 每階分支最多 3 個，跟 v0.3 一樣；現行每階預留 4 格（`MAX_BRANCH = 4`）夠用。如果**不重用**已移除的格，47 個新節點都放得進沒用過的格（附錄 A），不用擴充配置表。
- 有 7 個沿用的分支在 v0.4 表格裡排的位置跟 v0.3 不同（附錄 B）。格號就是 FormID，照 v0.4 表序重排會讓舊存檔的已購節點消失，所以格號要保持 v0.3 的，顯示順序另外記。
- 現有 perk 身上掛著引擎進入點（PRKE）的格，有很多在 v0.4 變成別的東西或被移除（例如 `ESSB_P_noform_0_0_M*` 的武器傷害、`ESSB_P_common_0_2_M*` 的受傷減免、冰盾／電盾／水鏡／影甲／星體……）。這些進入點一定要跟著刪或改，不然玩家會同時吃到舊的引擎效果和新的機制。

**設計文件內部不一致（實作前要請設計端確認，本盤點以各樹表格為準）**

1. 5 節開頭的骨架表說每棵元素樹都有「持續熟練主線：X 附傷 +1%／點」，但水的持續熟練是長流（native 也寫明 `kProcAdept` 水是 `kNoNode`）。
2. 骨架表說每棵元素樹都有「關閉專精主線：終焉後 5 秒內接管元素附傷 +1%／點」，但火（爆燃消耗加成）、土（地震削耐）、風（多段觸發）、血（血潮治療倍率）、暗（死咒係數）的表格不是這個。現行 `ESSBElem.psc` 約 617 行對**所有**元素樹的 (tree, 2, 2) 一律呼叫 `SetEndBoost`，只對冰雷聖毒水乘節點倍率——等於火／土／風／血／暗那一格的點數同時被當成「接管附傷」用，這是現有的 bug，重建時要一起修。
3. 骨架表說「開啟新手分支：開印時附近 1 人也 X」每樹都有，但火的開啟新手分支是「引火」、暗的是「夢魘」（暗的擴散型「暗染」在大師）。
4. 3 節寫 MCM「節點倍率」滑桿 1～5、預設 3；現行 `write_mcm` 產的是 0.25～3.0、預設 3，`validate_mcm` 也把 (0.25, 3.0, 0.05) 寫死。

## 2. 逐節點對照

欄位說明：「現有 perk」主線寫 15 階鏈的 EditorID 與 FormID 區間（本地 ID，載入時前面加外掛索引），分支寫單一 perk。「備註與接線」依序是：分類理由；`現行：` = `plan_coverage.py` 登記的實作位置；`Papyrus 直讀：` = 字面 `Rank`／`Br`／`GetBranch` 呼叫所在的腳本與次數；`Papyrus 共用：` = 各元素共用骨架用變數 `tree` 讀這一格的函式；**`DLL：`** = native 讀這一格的常數（round 20 工作樹）；`ESP 進入點：` = 這筆 perk 身上現在掛的 PERK 進入點。

### 5.3 火焰（`fire`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續（烈焰） | 新手 | 主線 | 火源倍率 N +0.2／點（2 → 5） | DLL N3 | `ESSB_P_fire_0_0_M1..M15` 0x004000–0x00400E | 熱度每層火附傷 +0.2%／點（8% → 11%） | **CHANGED** | 熱度從目標層數改為玩家三階；主線改買火源倍率 N；現行：ESSBElem.FireHitMult；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 1 | **添薪**：白熱引信 8 → 12 秒 | DLL N3 | `ESSB_P_fire_0_0_B1` 0x002000 | 添薪：熱度上限 10 → 15，自燃改在 15 層 | **CHANGED** | 熱度上限 → 白熱引信秒數；現行：ESSBElem.HeatCap → ESSBController.StackCap → ESSBStatus.AddS…；Papyrus 直讀：ESSBElem×1 |
|  | 熟練 | 主線 | 火附傷 +1%／點 | DLL N2 | `ESSB_P_fire_0_1_M1..M15` 0x00400F–0x00401D | 火附傷 +1%／點 | **SAME** | 現行：ESSBElem.FireHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcAdept[elem]** |
|  |  | 分支 1 | **烙印**：重擊使熱度升兩階 | DLL N3 | `ESSB_P_fire_0_1_B1` 0x002004 | 烙印：重擊熱度 +2 → +4 | **RETUNED** | 熱度單位由「層」改「階」：+2→+4 層改為升兩階；現行：ESSBElem.HitStacks；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **溫血**：火形態耐力回復 +20% | Papyrus | `ESSB_P_fire_0_1_B2` 0x002005 | 溫血：火形態耐力回復 +20% | **SAME** | 現行：SPEL ESSB_Ability_WarmBlood + ESSBController.RefreshAbilitie…；Papyrus 直讀：ESSBController×1 |
|  | 專精 | 主線 | 帶火印記目標火抗 -1%／點 | DLL N3 | `ESSB_P_fire_0_2_M1..M15` 0x00401E–0x00402C | 帶熱度目標火抗 -1%／點 | **RETUNED** | 條件由「帶熱度」改讀「帶火印記」（熱度已搬到玩家身上）；現行：ESSBElem.ApplyFireResistShred；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 1 | **熔心**：洩壓與過熱後保留微熱 | DLL N3 | `ESSB_P_fire_0_2_B1` 0x002008 | 熔心：自燃後熱度保留一半 | **CHANGED** | 自燃已不存在；改為洩壓／過熱後保留微熱；現行：ESSBElem.IgniteResidual；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **熔身**：過熱不付代價，改為進入 10 秒「熔身」：火附傷 +100%、每秒回耐力 5，期間熱度停在白熱不推進；結束後熱度歸零。熔身中切換或按 Z 仍是洩壓 | DLL N3＋引擎效果 | `ESSB_P_fire_0_2_B2` 0x002009 | 熔身：過熱滿了不再對自己爆，改為進入 10 秒「熔身」：火附傷 +100%、受傷 -20%、每秒回耐力 5，期間過熱不累積；結束後過熱歸零。熔身中按 Z 融斷仍可洩壓，以熔身剩餘秒數 ×2 計為過熱點數 | **CHANGED** | 拿掉「受傷 -20%」（現有 PERK 0x24 進入點要刪）；觸發改為過熱；現行：ESSBElem.HasMoltenBody → ESSBController.AddSelf/TickTimers +…；Papyrus 直讀：ESSBElem×1；ESP 進入點：0x24 |
|  | 大師 | 主線 | 同調每段火附傷 +1%／點 | DLL N2 | `ESSB_P_fire_0_3_M1..M15` 0x00402D–0x00403B | 同調每段火附傷 +1%／點 | **SAME** | 現行：ESSBElem.FireHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcMaster[elem]** |
|  |  | 分支 1 | **灼身**：被近戰命中時攻擊者掛火印記並受一次火傷，每 3 秒一次 | DLL 受擊 N4 | `ESSB_P_fire_0_3_B1` 0x00200C | 灼身：被近戰命中時攻擊者熱度 +1 並受一次火傷，每 3 秒一次 | **CHANGED** | 攻擊者熱度 +1 → 掛火印記；現行：ESSBGuard.OnHitEx |
|  |  | 分支 2 | **火浴**：白熱點燃當下依燒到的人數固定回血量，之後每秒回血 B_max ×0.1 × 該人數（人數不隨後續增減變動） | DLL N3 | `ESSB_P_fire_0_3_B2` 0x00200D | 火浴：自燃時你回血 B_max ×2 | **CHANGED** | 自燃回血 → 白熱點燃依人數回血＋每秒回血；現行：ESSBElem.OnIgnite；Papyrus 直讀：ESSBElem×1 |
|  | 傳奇 | 主線 | 業火，同調三段時火源倍率 N 再 +0.1／點（5 → 6.5，熔燒 8.5） | DLL N3 | `ESSB_P_fire_0_4_M1..M15` 0x00403C–0x00404A | 業火：同調三段時自燃倍率 +0.1／點（×2 → ×3.5） | **CHANGED** | 自燃倍率 → 火源倍率 N；現行：ESSBElem.IgniteMult；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 1 | **浴火**：同調三段時被帶火印記的目標命中，熱度推進一次（照成熟時間；已在白熱以上則無效），被圍毆時也能升到白熱 | DLL 受擊 N4 | `ESSB_P_fire_0_4_B1` 0x002010 | 浴火：同調三段時帶熱度目標對你的傷害 -30% | **CHANGED** | 受傷 -30%（現有 PERK 0x24 分頁 1）→ 被帶火印記者命中時推進熱度（DLL 受擊）；現行：PERK ESSB_P_fire_0_4_B1 進入點 0x24（分頁 1 = 攻擊者）；ESP 進入點：0x24 分頁1 |
|  |  | 分支 2 | **熔爐**：白熱引信到期不過熱，改升到第四階「熔燒」（火附傷 +90%、爆燃 ×4.0、火源 4.5 公尺、N +2）再燒 6 秒才過熱 | DLL N3 | `ESSB_P_fire_0_4_B2` 0x002011 | 熔爐：過熱上限 10 → 20，過熱中火附傷 +50% → +80% | **CHANGED** | 過熱上限 → 第四階熔燒；現行：ESSBElem.OverheatCap + ESSBElem.FireHitMult；Papyrus 直讀：ESSBElem×2 |
| 開啟（焰起） | 新手 | 主線 | 開印後 5 秒內熱度升階免等待，+0.5 秒／每 5 點 | DLL N3 | `ESSB_P_fire_1_0_M1..M15` 0x00404B–0x004059 | 開印熱度 +1／每 5 點 | **CHANGED** | 開印熱度 +1 → 開印後升階免等待秒數；現行：ESSBElem.OpenStacks；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 1 | **引火**：開印使熱度升兩階 | DLL N3 | `ESSB_P_fire_1_0_B1` 0x002014 | 引火：開印熱度 +2 → +5 | **RETUNED** | 熱度單位改階：+2→+5 層改為升兩階；現行：ESSBElem.OpenStacks；Papyrus 直讀：ESSBElem×1 |
|  | 熟練 | 主線 | 開印後 5 秒內火附傷 +1%／點 | DLL N3 | `ESSB_P_fire_1_1_M1..M15` 0x00405A–0x004068 | 開印後 5 秒內火附傷 +1%／點 | **SAME** | 現行：ESSBElem.FireHitMult（GetOpenBoost）；Papyrus 直讀：ESSBElem×1；Papyrus 共用：ESSBController.DifferencePossible／開印加成 |
|  |  | 分支 1 | **烈火點燃**：白熱中開印，白熱引信 +2 秒（每個引信最多 +4 秒）；火源掛的火印記不算開印 | DLL N3 | `ESSB_P_fire_1_1_B1` 0x002018 | 烈火點燃：開印那一擊附傷 ×1.5 | **CHANGED** | 開印那一擊 ×1.5 → 白熱中開印延長引信；現行：ESSBElem.OpenStrikeMult → ESSBController.ApplyProc；Papyrus 共用：ESSBElem.OpenStrikeMult ×1.5＋ESSBController.DifferencePossible（各元素共用） |
|  |  | 分支 2 | **餘熱**：開印時回復 15 耐力 | DLL N3 | `ESSB_P_fire_1_1_B2` 0x002019 | 餘熱：開印時回復 15 耐力 | **SAME** | 現行：ESSBElem.OpenFire；Papyrus 直讀：ESSBElem×1 |
|  | 專精 | 主線 | 火印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_fire_1_2_M1..M15` 0x004069–0x004077 | 火印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBElem.MarkDurationBonus → ESSBController.ApplyMark；Papyrus 共用：ESSBElem.MarkDurationBonus |
|  |  | 分支 1 | **焰起強化**：開印額外對範圍內敵人造成一次火附傷 | DLL N5 | `ESSB_P_fire_1_2_B1` 0x00201C | 焰起強化：焰起額外對範圍內敵人造成一次火附傷 | **SAME** | 措辭：「焰起」改稱「開印」；現行：ESSBElem.OpenFire；Papyrus 直讀：ESSBElem×1 |
|  | 大師 | 主線 | 火臨，開火形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | Papyrus＋DLL N5 | `ESSB_P_fire_1_3_M1..M15` 0x004078–0x004086 | 火臨：開火形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem.OnFormOpened → ESSBController.ForceOpenOn；Papyrus 共用：ESSBElem.OnFormOpened（X 臨） |
|  |  | 分支 1 | **烈火之始**：開印若目標生命高於 80%，你的熱度直接白熱 | DLL N3 | `ESSB_P_fire_1_3_B1` 0x002020 | 烈火之始：開印若目標生命高於 80%，熱度直接 8 | **RETUNED** | 熱度直接 8 → 直接白熱；現行：ESSBElem.OpenFire；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **火種**：微熱與灼熱不因未命中退階（白熱引信不變） | DLL N3 | `ESSB_P_fire_1_3_B2` 0x002021 | 火種：熱度不因未命中歸零，直到被切掉或自燃 | **RETUNED** | 不歸零 → 微熱／灼熱不退階；現行：ESSBElem.HasTinder → ESSBStatus.Tick；Papyrus 直讀：ESSBElem×1 |
|  | 傳奇 | 主線 | 開印效果 +3%／點 | DLL N3 | `ESSB_P_fire_1_4_M1..M15` 0x004087–0x004095 | 開印效果 +3%／點 | **SAME** | 現行：ESSBElem.OpenMult → ESSBReactions.Open；Papyrus 共用：ESSBElem.OpenMult |
|  |  | 分支 1 | **先燃**：同調三段時開印立即一次 ×0.5 爆燃（不消耗目標狀態） | DLL N3 | `ESSB_P_fire_1_4_B1` 0x002024 | 先燃：同調三段時開印立即一次 ×0.5 爆燃 | **SAME** | v0.4 只補充說明；現行：ESSBElem.OpenFire → ESSBElem.Detonate；Papyrus 直讀：ESSBElem×1 |
| 關閉（爆燃） | 新手 | 主線 | 終焉 +2%／點 | DLL N3（融斷 N5） | `ESSB_P_fire_2_0_M1..M15` 0x004096–0x0040A4 | 終焉 +2%／點 | **SAME** | 現行：ESSBElem.EndMult；Papyrus 共用：ESSBElem.EndMult |
|  |  | 分支 1 | **猛爆**：爆燃不消耗目標身上的狀態（吃了加成但東西還在） | DLL N3 | `ESSB_P_fire_2_0_B1` 0x002028 | 猛爆：爆燃不消耗熱度 | **CHANGED** | 不消耗熱度 → 不消耗目標身上其他元素狀態；現行：ESSBElem.Detonate；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **餘壓**：白熱期間切換或融斷後熱度保留灼熱，且火源多留 2 秒 | Papyrus＋DLL N3 | （無） | — | **NEW** | 白熱中切換／融斷保留灼熱，火源多留 2 秒；— |
|  |  | （移除） | — | — | `ESSB_P_fire_2_0_B2` 0x002029 | 洩壓：融斷時把過熱轉為額外爆燃傷害，每點過熱 +10% | **REMOVED** | 白熱中切換／融斷的「洩壓」改成基礎機制（火基礎表）；現行：ESSBElem.VentMult；Papyrus 直讀：ESSBElem×1 |
|  | 熟練 | 主線 | 火印記的融斷 +2%／點 | DLL N5 | `ESSB_P_fire_2_1_M1..M15` 0x0040A5–0x0040B3 | 火印記的融斷 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **熾焰**：白熱以上的爆燃再 ×1.5 | DLL N3 | `ESSB_P_fire_2_1_B1` 0x00202C | 熾焰：爆燃結算時若熱度 ≥8 則 ×1.5 | **RETUNED** | 熱度 ≥8 → 白熱以上；現行：ESSBElem.Detonate；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **熔斷**：融斷後熱度保留 | DLL N5 | `ESSB_P_fire_2_1_B2` 0x00202D | 熔斷：融斷後目標熱度保留 | **RETUNED** | 保留的是玩家熱度（原本是目標熱度）；現行：ESSBElem.KeepHeatOnBurst → ESSBElem.EndFireNodes；Papyrus 直讀：ESSBElem×1 |
|  | 專精 | 主線 | 爆燃的消耗加成 +1%／點 × 被消耗的狀態數 | DLL N3 | `ESSB_P_fire_2_2_M1..M15` 0x0040B4–0x0040C2 | 爆燃每層熱度倍率 +0.01／點（0.2 → 0.35） | **CHANGED** | 每層熱度倍率 → 消耗加成 × 被吃掉的狀態數；現行：ESSBElem.DetonatePerLayer；Papyrus 直讀：ESSBElem×1；Papyrus 共用：ESSBElem（SetEndBoost，任何樹這格有點數都會觸發） |
|  |  | 分支 1 | **餘燼**：火終焉後接管元素的開印 ×1.5 | DLL N3 | `ESSB_P_fire_2_2_B1` 0x002030 | 餘燼：火終焉後接管元素的開印 ×1.5 | **SAME** | 現行：ESSBElem.EndFireNodes → ESSBStatus.SetNextOpenMult；Papyrus 直讀：ESSBElem×1 |
|  | 大師 | 主線 | 火印記的融斷再 +2%／點 | DLL N5 | `ESSB_P_fire_2_3_M1..M15` 0x0040C3–0x0040D1 | 火印記的融斷再 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **焚天**：火終焉觸發時，範圍內所有帶火印記目標一起爆燃（各自吃自己身上的狀態） | DLL N5 | `ESSB_P_fire_2_3_B1` 0x002034 | 焚天：火終焉觸發時，範圍內所有帶熱度目標一起爆燃（各自吃自己的熱度） | **RETUNED** | 帶熱度 → 帶火印記；現行：ESSBElem.EndFireNodes；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **火葬**：爆燃擊殺的目標對附近敵人再爆一次 ×0.5 | DLL N5 | `ESSB_P_fire_2_3_B2` 0x002035 | 火葬：爆燃擊殺的目標對附近敵人再爆一次 ×0.5 | **SAME** | 現行：ESSBElem.Detonate；Papyrus 直讀：ESSBElem×1 |
|  | 傳奇 | 主線 | 爆燃 +3%／點 | DLL N3（融斷 N5） | `ESSB_P_fire_2_4_M1..M15` 0x0040D2–0x0040E0 | 爆燃 +3%／點 | **SAME** | 現行：ESSBElem.SignatureMult；Papyrus 共用：ESSBElem.SignatureMult |
|  |  | 分支 1 | **火域**：火印記融斷後留下 5 秒火域，內部敵人受火傷 +20%、你在其中熱度升階免等待，且進入火域時白熱引信一次性 +5 秒 | Papyrus（領域）；引信延長：DLL N3（進入時一次寫入，非每秒暫停） | `ESSB_P_fire_2_4_B1` 0x002038 | 火域：火印記融斷後留下 5 秒火域，內部敵人受火傷 +20%、你的熱度累積 ×2 | **CHANGED** | 熱度累積 ×2 → 升階免等待＋引信一次 +5 秒；現行：ESSBElem.EndFireNodes → ESSBController.StartDomain；Papyrus 直讀：ESSBElem×1 |

### 5.4 冰霜（`frost`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續（凍結） | 新手 | 主線 | 每次命中凍結累積 +5%／點（小數以機率取整） | DLL N3 | `ESSB_P_frost_0_0_M1..M15` 0x0040E1–0x0040EF | 每次命中凍結累積 +5%／點 | **SAME** | v0.4 只補充說明；現行：ESSBElem.HitStacks；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 1 | **寒蝕**：重擊凍結再 +1（總計 +3），且該次重擊造成的凍結歸零時限延長 2 秒（可調） | DLL N3 | `ESSB_P_frost_0_0_B1` 0x00203C | 寒蝕：重擊凍結 +2 | **RETUNED** | 重擊凍結 +2 → 再 +1（總 +3），另加歸零時限 +2 秒；現行：ESSBElem.HitStacks；Papyrus 直讀：ESSBElem×1 |
|  | 熟練 | 主線 | 冰附傷 +1%／點 | DLL N2 | `ESSB_P_frost_0_1_M1..M15` 0x0040F0–0x0040FE | 冰附傷 +1%／點 | **SAME** | 現行：ESSBElem.FrostHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcAdept[elem]** |
|  |  | 分支 1 | **深寒**：冰封中目標耐力不回復，攻擊 -20% | 引擎效果 | `ESSB_P_frost_0_1_B1` 0x002040 | 深寒：冰封中目標耐力不回復，攻擊 -20% | **SAME** | 現行：ESSBElem.OnFrozenTick；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **霜膚**：冰甲寒氣半徑 3 → 5 公尺，寒氣減速再 +10% | 引擎效果 | `ESSB_P_frost_0_1_B2` 0x002041 | 霜膚：冰形態受傷 -5% | **CHANGED** | 冰形態受傷 -5%（現有 PERK 0x24 要刪）→ 冰甲寒氣半徑與減速；現行：PERK ESSB_P_frost_0_1_B2 進入點 0x24；ESP 進入點：0x24 |
|  | 專精 | 主線 | 冰封目標受冰附傷 +2%／點 | DLL N3 | `ESSB_P_frost_0_2_M1..M15` 0x0040FF–0x00410D | 冰封目標受冰附傷 +2%／點 | **SAME** | 現行：ESSBElem.FrostHitMult；Papyrus 直讀：ESSBController×1、ESSBElem×1 |
|  |  | 分支 1 | **永凍**：冰封 +2 秒，結束後凍結保留一半 | DLL N3 | `ESSB_P_frost_0_2_B1` 0x002044 | 永凍：冰封 +2 秒，結束後凍結保留一半 | **SAME** | 現行：ESSBElem.FrozenExtraSeconds / FrozenResidual → ESSBStatus.Ti…；Papyrus 直讀：ESSBElem×2 |
|  |  | 分支 2 | **連鎖冰封**：冰封目標死亡時附近敵人凍結 +3 並減速 30% 3 秒 | DLL N5 | `ESSB_P_frost_0_2_B2` 0x002045 | 連鎖冰封：冰封目標死亡時附近敵人凍結 +3 並減速 30% 3 秒 | **SAME** | 現行：ESSBElem.OnKill → ESSBController.Tick；Papyrus 直讀：ESSBElem×1 |
|  | 大師 | 主線 | 同調每段冰附傷 +1%／點 | DLL N2 | `ESSB_P_frost_0_3_M1..M15` 0x00410E–0x00411C | 同調每段冰附傷 +1%／點 | **SAME** | 現行：ESSBElem.FrostHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcMaster[elem]** |
|  |  | 分支 1 | **冰鎧**：冰盾上限 5 → 8 層 | DLL N4 | （無） | — | **NEW** | 冰盾上限 5 → 8（冰盾本身改成基礎機制）；— |
|  |  | 分支 2 | **凍傷**：冰封結束時沒被碎掉的冰晶不浪費，每顆轉為一次 B_max ×0.5 冰傷 | DLL N3 | （無） | — | **NEW** | 冰封結束沒碎的冰晶轉冰傷；— |
|  |  | 分支 3 | **寒反**：攻擊你的敵人被減速，且凍結 +1（每目標 3 秒一次） | DLL 受擊 N4 | `ESSB_P_frost_0_3_B2` 0x002049 | 寒反：攻擊你的敵人被減速 | **RETUNED** | 加上凍結 +1、每目標 3 秒冷卻；現行：ESSBGuard.OnHitEx |
|  |  | （移除） | — | — | `ESSB_P_frost_0_3_B1` 0x002048 | 冰盾：每命中 +1 層（最多 5），被打消耗一層抵消該次 30% 傷害 | **REMOVED** | 冰盾改成冰形態基礎機制（這格有 PERK 0x24，且 ESSBController.RefreshRecovery 用 SetNthEntryValue 改它）；現行：ESSBController.AddIceShield + PERK ESSB_P_frost_0_3_B1 進入點 0…；Papyrus 直讀：ESSBController(GetBranch+SetNthEntryValue)×1；ESP 進入點：0x24 |
|  | 傳奇 | 主線 | 絕對零度，同調三段時冰封減速再 -2%／點（總減速上限 70%），可影響首領 | DLL N3 | `ESSB_P_frost_0_4_M1..M15` 0x00411D–0x00412B | 絕對零度：同調三段時冰封減速再 -2%／點（自有強減速，非麻痺），可影響首領 | **SAME** | 措辭；明寫總減速上限 70%；現行：ESSBElem.OnFrozenTick；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 1 | **冰心**：生命低於 30% 時自動冰封附近所有凍結量表 ≥1 的敵人，每 30 秒一次 | DLL 受擊 N4 | `ESSB_P_frost_0_4_B1` 0x00204C | 冰心：生命低於 30% 時自動冰封附近所有帶寒意的敵人，每 30 秒一次 | **RETUNED** | 「帶寒意」→「凍結量表 ≥1」；現行：ESSBElem.OnTick → ESSBController.TakeIceHeart；Papyrus 直讀：ESSBElem×1 |
| 開啟（冰臨） | 新手 | 主線 | 開印凍結 +1／每 3 點 | DLL N3 | `ESSB_P_frost_1_0_M1..M15` 0x00412C–0x00413A | 開印凍結 +1／每 3 點 | **SAME** | 現行：ESSBElem.OpenStacks；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 1 | **寒潮**：開印時附近 1 人凍結 +2 | DLL N3（掃描 N5） | `ESSB_P_frost_1_0_B1` 0x002050 | 寒潮：開印時附近 1 人凍結 +2 | **SAME** | 現行：ESSBElem.OpenFrost → ESSBController.AddStackTo；Papyrus 直讀：ESSBElem×1 |
|  | 熟練 | 主線 | 開印後 5 秒內冰附傷 +1%／點 | DLL N3 | `ESSB_P_frost_1_1_M1..M15` 0x00413B–0x004149 | 開印後 5 秒內冰附傷 +1%／點 | **SAME** | 現行：ESSBElem.FrostHitMult（GetOpenBoost）；Papyrus 直讀：ESSBElem×1；Papyrus 共用：ESSBController.DifferencePossible／開印加成 |
|  |  | 分支 1 | **深霜結**：開印時在目標身上預存 1 顆冰晶（冰封後不用普攻就有 1 顆；上限仍是 3） | DLL N3 | `ESSB_P_frost_1_1_B1` 0x002054 | 深霜結：開印那一擊附傷 ×1.5 | **CHANGED** | 開印 ×1.5 → 預存 1 顆冰晶；現行：ESSBElem.OpenStrikeMult；Papyrus 共用：ESSBElem.OpenStrikeMult ×1.5＋ESSBController.DifferencePossible（各元素共用） |
|  |  | 分支 2 | **冰甲**：冰形態下你身上一圈 3 公尺寒氣（披風，只對敵對者）：範圍內敵人減速 20%，凍結量表 ≥1 的改為 35%（取最強不相加，受 70% 上限）；你命中寒氣內的敵人時凍結再 +1 | Papyrus（掛披風）＋引擎效果；命中加凍結：DLL N3 | `ESSB_P_frost_1_1_B2` 0x002055 | 冰甲：開印時獲得 1 層冰盾 | **CHANGED** | 開印得 1 層冰盾 → 冰形態 3 公尺寒氣披風；現行：ESSBElem.OpenFrost；Papyrus 直讀：ESSBElem×1 |
|  | 專精 | 主線 | 冰印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_frost_1_2_M1..M15` 0x00414A–0x004158 | 冰印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBElem.MarkDurationBonus；Papyrus 共用：ESSBElem.MarkDurationBonus |
|  |  | 分支 1 | **冰臨強化**：冰臨附帶減速 30% 3 秒 | Papyrus＋DLL N5 | `ESSB_P_frost_1_2_B1` 0x002058 | 冰臨強化：冰臨附帶減速 30% 3 秒 | **SAME** | 現行：ESSBElem.OnFormOpened；Papyrus 直讀：ESSBElem×1 |
|  | 大師 | 主線 | 冰臨，開冰形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | Papyrus＋DLL N5 | `ESSB_P_frost_1_3_M1..M15` 0x004159–0x004167 | 冰臨：開冰形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem.OnFormOpened；Papyrus 共用：ESSBElem.OnFormOpened（X 臨） |
|  |  | 分支 1 | **霜鎖**：開印目標 3 秒內移速 -30%；目標已在減速上限（70%）時改為凍結 +1 | DLL N3 | `ESSB_P_frost_1_3_B1` 0x00205C | 霜鎖：開印目標 3 秒內移速 -30% | **RETUNED** | 加上「已到減速上限改凍結 +1」；現行：ESSBElem.OpenFrost；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **霜爆**：目標進入冰封的那一刻，3 公尺內其他凍結量表 ≥1 的敵人凍結 +2 | DLL N3（掃描 N5） | （無） | — | **NEW** | 進入冰封時 3 公尺內凍結 +2；— |
|  |  | （移除） | — | — | `ESSB_P_frost_1_3_B2` 0x00205D | 冰晶：開印時你受傷 -10% 3 秒 | **REMOVED** | 開印時受傷 -10%（PERK 0x24，讀 GuardIce 視窗）；現行：ESSBElem.OpenFrost + PERK ESSB_P_frost_1_3_B2 進入點 0x24；Papyrus 直讀：ESSBElem×1；ESP 進入點：0x24 |
|  | 傳奇 | 主線 | 開印效果 +3%／點 | DLL N3 | `ESSB_P_frost_1_4_M1..M15` 0x004168–0x004176 | 開印效果 +3%／點 | **SAME** | 現行：ESSBElem.OpenMult；Papyrus 共用：ESSBElem.OpenMult |
|  |  | 分支 1 | **絕霜**：同調三段時開印直接冰封 | DLL N3 | `ESSB_P_frost_1_4_B1` 0x002060 | 絕霜：同調三段時開印直接冰封 | **SAME** | 現行：ESSBElem.OpenFrost；Papyrus 直讀：ESSBElem×1 |
| 關閉（碎冰） | 新手 | 主線 | 終焉 +2%／點 | DLL N3（融斷 N5） | `ESSB_P_frost_2_0_M1..M15` 0x004177–0x004185 | 終焉 +2%／點 | **SAME** | 現行：ESSBElem.EndMult；Papyrus 共用：ESSBElem.EndMult |
|  |  | 分支 1 | **銳碎**：碎冰 20% → 25%（首領 10% → 12%） | DLL N3 | `ESSB_P_frost_2_0_B1` 0x002064 | 銳碎：處決門檻 20% → 30% | **CHANGED** | 處決門檻 20→30% → 碎冰真傷 20→25%（碎冰由處決改為最大生命百分比）；現行：ESSBElem.ShatterThreshold；Papyrus 直讀：ESSBElem×1 |
|  | 熟練 | 主線 | 冰印記的融斷 +2%／點 | DLL N5 | `ESSB_P_frost_2_1_M1..M15` 0x004186–0x004194 | 冰印記的融斷 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **冰崩**：碎冰範圍化為 3 公尺，終焉碎冰與冰封中重擊碎冰皆適用，命中範圍內所有冰封目標（各吃自己的冰晶） | DLL N5 | `ESSB_P_frost_2_1_B1` 0x002068 | 冰崩：碎冰改為 3 公尺範圍，命中所有冰封目標 | **RETUNED** | 明寫兩種碎冰時機都適用、各吃冰晶；現行：ESSBElem.ShatterArea；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **冰封融斷**：冰印記融斷時目標若冰封，視同碎冰 | DLL N5 | `ESSB_P_frost_2_1_B2` 0x002069 | 冰封融斷：冰印記融斷時目標若冰封，視同碎冰，含處決判定 | **RETUNED** | 拿掉處決判定；現行：ESSBElem.FrostBurstShatter → ESSBReactions.EndFrost；Papyrus 直讀：ESSBElem×1 |
|  | 專精 | 主線 | 終焉後 5 秒內接管元素附傷 +1%／點 | DLL N3 | `ESSB_P_frost_2_2_M1..M15` 0x004195–0x0041A3 | 終焉後 5 秒內接管元素附傷 +1%／點 | **SAME** | 現行：ESSBElem.OnEnd → ESSBController.SetEndBoost；Papyrus 共用：ESSBElem（SetEndBoost，任何樹這格有點數都會觸發） |
|  |  | 分支 1 | **寒留**：冰終焉後接管元素的印記持續 +4 秒 | DLL N3 | `ESSB_P_frost_2_2_B1` 0x00206C | 寒留：冰終焉後接管元素的印記持續 +4 秒 | **SAME** | 現行：ESSBElem.EndFrostNodes → ESSBController.SetNextMarkBonus；Papyrus 直讀：ESSBElem×1 |
|  | 大師 | 主線 | 冰印記的融斷再 +2%／點 | DLL N5 | `ESSB_P_frost_2_3_M1..M15` 0x0041A4–0x0041B2 | 冰印記的融斷再 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **冰河**：冰終焉時目標若冰封，範圍內所有冰封目標一起碎冰 | DLL N5 | `ESSB_P_frost_2_3_B1` 0x002070 | 冰河：冰終焉時目標若冰封，範圍內所有冰封目標一起碎冰，各自獨立判定處決 | **RETUNED** | 拿掉各自處決判定；現行：ESSBElem.EndFrostNodes → ShatterArea；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **碎甲加深**：碎冰的碎甲 10% → 20% | DLL N3 | `ESSB_P_frost_2_3_B2` 0x002071 | 碎甲加深：碎冰的碎甲 10% → 20% | **SAME** | 現行：ESSBElem.Shatter；Papyrus 直讀：ESSBElem×1 |
|  | 傳奇 | 主線 | 碎冰 +3%／點（乘在 20% 上） | DLL N3 | `ESSB_P_frost_2_4_M1..M15` 0x0041B3–0x0041C1 | 碎冰 +3%／點 | **RETUNED** | 碎冰語意改為最大生命百分比，+3%／點乘在 20% 上；現行：ESSBElem.SignatureMult；Papyrus 共用：ESSBElem.SignatureMult |
|  |  | 分支 1 | **冰棺**：碎冰後目標再冰封 2 秒（第二次碎冰 ×0.5） | DLL N3 | `ESSB_P_frost_2_4_B1` 0x002074 | 冰棺：碎冰未處決的目標再冰封 2 秒 | **RETUNED** | 未處決 → 碎冰後；第二次碎冰 ×0.5；現行：ESSBElem.Shatter；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **冰原**：冰印記融斷後留下 5 秒冰原，內部敵人減速 50%、凍結累積 ×2，你在其中免疫減速 | Papyrus（領域） | `ESSB_P_frost_2_4_B2` 0x002075 | 冰原：冰印記融斷後留下 5 秒冰原，內部敵人減速 50%、凍結累積 ×2，你在其中免疫減速 | **SAME** | 現行：ESSBElem.EndFrostNodes → ESSBController.StartDomain/TickDoma…；Papyrus 直讀：ESSBElem×1 |

### 5.5 雷電（`lightning`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續（充能） | 新手 | 主線 | 放電每格電荷傷害 +1%／點 | DLL N3 | `ESSB_P_lightning_0_0_M1..M15` 0x0041C2–0x0041D0 | 放電每格電荷傷害 +1%／點 | **SAME** | 現行：ESSBElem.Discharge；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 1 | **感應**：雷形態魔力回復 +20% | Papyrus | `ESSB_P_lightning_0_0_B1` 0x002078 | 感應：雷形態魔力回復 +20% | **SAME** | 現行：SPEL ESSB_Ability_Induction + ESSBController.RefreshAbilitie…；Papyrus 直讀：ESSBController×1 |
|  | 熟練 | 主線 | 雷附傷 +1%／點 | DLL N2 | `ESSB_P_lightning_0_1_M1..M15` 0x0041D1–0x0041DF | 雷附傷 +1%／點 | **SAME** | 現行：ESSBElem.ShockHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcAdept[elem]** |
|  |  | 分支 1 | **電弧**：放電跳躍人數 2 → 3 人，跳躍傷害 40% → 55%（可調） | DLL N3 | `ESSB_P_lightning_0_1_B1` 0x00207C | 電弧：放電時向附近 2 人跳躍 40% | **RETUNED** | 基礎放電已跳 2 人 40%；分支改為 3 人 55%；現行：ESSBElem.Discharge；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **靜電**：被近戰命中時攻擊者感電 | DLL 受擊 N4 | `ESSB_P_lightning_0_1_B2` 0x00207D | 靜電：被近戰命中時攻擊者感電 | **SAME** | 現行：ESSBGuard.OnHitEx |
|  | 專精 | 主線 | 電荷上限 +1／每 3 點 | DLL N4 | `ESSB_P_lightning_0_2_M1..M15` 0x0041E0–0x0041EE | 電荷上限 +1／每 3 點 | **SAME** | 現行：ESSBElem.ChargeCap → ESSBController.AddSelf；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 1 | **雷暴**：電荷滿時普攻也有 30% 機率放電（普攻放電清空電荷，但不必定暴擊） | DLL N4 | `ESSB_P_lightning_0_2_B1` 0x002080 | 雷暴：電荷滿時普攻也有 30% 機率放電 | **SAME** | v0.4 只補充說明；現行：ESSBElem.StormChance → ESSBController.OnWeaponHit；Papyrus 直讀：ESSBElem×1 |
|  | 大師 | 主線 | 同調每段雷附傷 +1%／點 | DLL N2 | `ESSB_P_lightning_0_3_M1..M15` 0x0041EF–0x0041FD | 同調每段雷附傷 +1%／點 | **SAME** | 現行：ESSBElem.ShockHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcMaster[elem]** |
|  |  | 分支 1 | **逆電**：被命中時電荷 +1（每 2 秒一次），挨打也在充電 | DLL 受擊 N4 | （無） | — | **NEW** | 被命中電荷 +1（每 2 秒）；— |
|  |  | 分支 2 | **疾電**：任何放電後 3 秒內暴擊率 +15% | 引擎效果（放電時由 DLL N4 掛上） | `ESSB_P_lightning_0_3_B2` 0x002085 | 疾電：放電後 3 秒受傷 -15% | **CHANGED** | 放電後受傷 -15%（現有 PERK 0x24）→ 暴擊率 +15%（引擎效果）；現行：ESSBElem.Discharge + PERK ESSB_P_lightning_0_3_B2 進入點 0x24；Papyrus 直讀：ESSBElem×1；ESP 進入點：0x24 |
|  |  | （移除） | — | — | `ESSB_P_lightning_0_3_B1` 0x002084 | 電盾：電荷 ≥5 時受傷 -15% | **REMOVED** | 電荷 ≥5 受傷 -15%（PERK 0x24；ESSBController.RefreshRecovery 用 SetNthEntryValue 改這格）；現行：PERK ESSB_P_lightning_0_3_B1 進入點 0x24；Papyrus 直讀：ESSBController(GetBranch+SetNthEntryValue)×1；ESP 進入點：0x24 |
|  | 傳奇 | 主線 | 天雷，同調三段時放電改為對範圍內所有感電目標，範圍 2 公尺 +0.2 公尺／點 | DLL N5 | `ESSB_P_lightning_0_4_M1..M15` 0x0041FE–0x00420C | 天雷：同調三段時放電改為對範圍內所有感電目標，範圍 2 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem.DischargeAll；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 1 | **雷神**：同調三段時電荷一到滿層，立即對被命中的目標自動放電並回復魔力 | DLL N4 | `ESSB_P_lightning_0_4_B1` 0x002088 | 雷神：同調三段時電荷滿層自動放電並回復魔力 | **SAME** | v0.4 只補充說明（對被命中的目標放電）；現行：ESSBElem.OnTick；Papyrus 直讀：ESSBElem×1 |
| 開啟（雷臨） | 新手 | 主線 | 開印電荷 +1／每 5 點 | DLL N4 | `ESSB_P_lightning_1_0_M1..M15` 0x00420D–0x00421B | 開印電荷 +1／每 5 點 | **SAME** | 現行：ESSBElem.OpenStacks；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 1 | **傳導**：開印時附近 1 人也感電 | DLL N3（掃描 N5） | `ESSB_P_lightning_1_0_B1` 0x00208C | 傳導：開印時附近 1 人也感電 | **SAME** | 現行：ESSBElem.OpenShock；Papyrus 直讀：ESSBElem×1 |
|  | 熟練 | 主線 | 開印後 5 秒內雷附傷 +1%／點 | DLL N3 | `ESSB_P_lightning_1_1_M1..M15` 0x00421C–0x00422A | 開印後 5 秒內雷附傷 +1%／點 | **SAME** | 現行：ESSBElem.ShockHitMult（GetOpenBoost）；Papyrus 直讀：ESSBElem×1；Papyrus 共用：ESSBController.DifferencePossible／開印加成 |
|  |  | 分支 1 | **強感電**：開印那一擊若是重擊，電荷直接補滿（這一擊本身不放電，下一次滿格重擊才放），每 15 秒一次 | DLL N4 | `ESSB_P_lightning_1_1_B1` 0x002090 | 強感電：開印那一擊附傷 ×1.5 | **CHANGED** | 開印 ×1.5 → 開印重擊補滿電荷；現行：ESSBElem.OpenStrikeMult；Papyrus 共用：ESSBElem.OpenStrikeMult ×1.5＋ESSBController.DifferencePossible（各元素共用） |
|  |  | 分支 2 | **充能開印**：開印時回復 B_max 魔力 | DLL N3 | `ESSB_P_lightning_1_1_B2` 0x002091 | 充能開印：開印時回復 B_max 魔力 | **SAME** | 現行：ESSBElem.OpenShock；Papyrus 直讀：ESSBElem×1 |
|  | 專精 | 主線 | 雷印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_lightning_1_2_M1..M15` 0x00422B–0x004239 | 雷印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBElem.MarkDurationBonus；Papyrus 共用：ESSBElem.MarkDurationBonus |
|  |  | 分支 1 | **雷臨強化**：雷臨時立即獲得 5 電荷 | Papyrus＋DLL N4 | `ESSB_P_lightning_1_2_B1` 0x002094 | 雷臨強化：雷臨時立即獲得 5 電荷 | **SAME** | 現行：ESSBElem.OnFormOpened；Papyrus 直讀：ESSBElem×1 |
|  | 大師 | 主線 | 雷臨，開雷形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | Papyrus＋DLL N5 | `ESSB_P_lightning_1_3_M1..M15` 0x00423A–0x004248 | 雷臨：開雷形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem.OnFormOpened；Papyrus 共用：ESSBElem.OnFormOpened（X 臨） |
|  |  | 分支 1 | **感電削弱**：感電目標魔抗 -10% | 引擎效果 | `ESSB_P_lightning_1_3_B1` 0x002098 | 感電削弱：感電目標魔抗 -10% | **SAME** | 現行：ESSBElem.OpenShock（自有 MagicResistDebuff）；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **雷閃**：開印後 2 秒移速 +15% | DLL N3 | `ESSB_P_lightning_1_3_B2` 0x002099 | 雷閃：開印後 2 秒移速 +15% | **SAME** | 現行：ESSBElem.OpenShock（自有 Haste）；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 3 | **雷鳴**：開印那一擊若暴擊，電荷額外 +2 | DLL N4 | （無） | — | **NEW** | 開印暴擊時電荷 +2；— |
|  |  | （移除） | — | — | `ESSB_P_lightning_1_3_B3` 0x00209A | 電蝕：削減的目標魔力 50% → 100%，目標魔力為 0 時你的雷附傷 +25% | **REMOVED** | 削魔 50→100%（雷滿格改為法術麻痺）；現行：ESSBElem.Discharge + ESSBElem.ShockHitMult；Papyrus 直讀：ESSBController×1、ESSBElem×2 |
|  | 傳奇 | 主線 | 開印效果 +3%／點 | DLL N3 | `ESSB_P_lightning_1_4_M1..M15` 0x004249–0x004257 | 開印效果 +3%／點 | **SAME** | 現行：ESSBElem.OpenMult；Papyrus 共用：ESSBElem.OpenMult |
|  |  | 分支 1 | **先雷**：同調三段時開印立即放電一次，不消耗電荷 | DLL N3 | `ESSB_P_lightning_1_4_B1` 0x00209C | 先雷：同調三段時開印立即放電一次，不消耗電荷 | **SAME** | 現行：ESSBElem.OpenShock；Papyrus 直讀：ESSBElem×1 |
| 關閉（放電） | 新手 | 主線 | 終焉 +2%／點 | DLL N3（融斷 N5） | `ESSB_P_lightning_2_0_M1..M15` 0x004258–0x004266 | 終焉 +2%／點 | **SAME** | 現行：ESSBElem.EndMult；Papyrus 共用：ESSBElem.EndMult |
|  |  | 分支 1 | **連鎖**：放電跳躍 2 → 5 人 | DLL N3 | `ESSB_P_lightning_2_0_B1` 0x0020A0 | 連鎖：放電跳躍 2 → 5 人 | **SAME** | 現行：ESSBElem.Discharge；Papyrus 直讀：ESSBElem×1 |
|  | 熟練 | 主線 | 雷印記的融斷 +2%／點 | DLL N5 | `ESSB_P_lightning_2_1_M1..M15` 0x004267–0x004275 | 雷印記的融斷 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **蓄餘**：雷終焉不消耗電荷 | DLL N3 | `ESSB_P_lightning_2_1_B1` 0x0020A4 | 蓄餘：雷終焉不消耗電荷 | **SAME** | 現行：ESSBElem.Discharge；Papyrus 直讀：ESSBController×1、ESSBElem×2 |
|  |  | 分支 2 | **雷斷**：雷印記融斷時附加你全部電荷的放電加成 | DLL N5 | `ESSB_P_lightning_2_1_B2` 0x0020A5 | 雷斷：雷印記融斷時附加你全部電荷的放電加成 | **SAME** | 現行：ESSBElem.ShockBurstBonus；Papyrus 直讀：ESSBElem×1 |
|  | 專精 | 主線 | 終焉後 5 秒內接管元素附傷 +1%／點 | DLL N3 | `ESSB_P_lightning_2_2_M1..M15` 0x004276–0x004284 | 終焉後 5 秒內接管元素附傷 +1%／點 | **SAME** | 現行：ESSBElem.OnEnd → ESSBController.SetEndBoost；Papyrus 共用：ESSBElem（SetEndBoost，任何樹這格有點數都會觸發） |
|  |  | 分支 1 | **餘電**：雷終焉後接管元素的開印附帶一次 ×0.5 放電 | DLL N3 | `ESSB_P_lightning_2_2_B1` 0x0020A8 | 餘電：雷終焉後接管元素的開印附帶一次 ×0.5 放電 | **SAME** | 現行：ESSBElem.EndShockNodes → ESSBController.SetPendingDischarge/…；Papyrus 直讀：ESSBElem×1 |
|  | 大師 | 主線 | 雷印記的融斷再 +2%／點 | DLL N5 | `ESSB_P_lightning_2_3_M1..M15` 0x004285–0x004293 | 雷印記的融斷再 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **雷殛**：雷終焉對範圍內所有感電目標各一次全額放電 | DLL N5 | `ESSB_P_lightning_2_3_B1` 0x0020AC | 雷殛：雷終焉對範圍內所有感電目標各一次全額放電 | **SAME** | 現行：ESSBElem.EndShockNodes；Papyrus 直讀：ESSBElem×1 |
|  |  | 分支 2 | **過載終焉**：任一元素終焉時，若你電荷 ≥8（電荷跨形態攜帶，10 秒未命中仍歸零），該次終焉傷害 ×2 | DLL N3 | `ESSB_P_lightning_2_3_B2` 0x0020AD | 過載終焉：終焉時電荷 ≥8 則傷害 ×2 | **RETUNED** | 明寫「任一元素終焉」與電荷跨形態攜帶；現行：ESSBElem.OverloadMult；Papyrus 直讀：ESSBElem×1 |
|  | 傳奇 | 主線 | 放電 +3%／點 | DLL N3（融斷 N5） | `ESSB_P_lightning_2_4_M1..M15` 0x004294–0x0042A2 | 放電 +3%／點 | **SAME** | 現行：ESSBElem.SignatureMult；Papyrus 共用：ESSBElem.SignatureMult |
|  |  | 分支 1 | **雷霆**：雷印記融斷後 5 秒內你每次命中都放電 ×0.3 | DLL N4 | `ESSB_P_lightning_2_4_B1` 0x0020B0 | 雷霆：雷印記融斷後 5 秒內你每次命中都放電 ×0.3 | **SAME** | 現行：ESSBElem.EndShockNodes → ESSBController.OnWeaponHit；Papyrus 直讀：ESSBElem×1 |

### 5.6 大地（`earth`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續（裂甲） | 新手 | 主線 | 裂痕護甲削減 +2／點（-30 → -60） | DLL N3 | `ESSB_P_earth_0_0_M1..M15` 0x0042A3–0x0042B1 | 裂痕護甲削減 +2／點（-30 → -60） | **SAME** | 現行：ESSBElem2.FissureArmor → ESSBReactions.Open(4)；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **磐石**：岩甲每層護甲 +25 → +40 | DLL N4 | `ESSB_P_earth_0_0_B1` 0x0020B4 | 磐石：岩甲每層護甲 +15 → +25 | **RETUNED** | +15→+25 改為 +25→+40（基礎岩甲每層護甲也上調）；現行：ESSBElem2.RockArmorPerLayer → ESSBController.SyncRockArmor；Papyrus 直讀：ESSBElem2×1 |
|  | 熟練 | 主線 | 土附傷 +1%／點 | DLL N2 | `ESSB_P_earth_0_1_M1..M15` 0x0042B2–0x0042C0 | 土附傷 +1%／點 | **SAME** | 現行：ESSBElem2.EarthHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcAdept[elem]** |
|  |  | 分支 1 | **震擊**：重擊消耗裂痕標記，觸發 1.5× 地震爆傷並削減 50 耐力 | DLL N3 | `ESSB_P_earth_0_1_B1` 0x0020B8 | 震擊：重擊消耗滿層裂痕，1.5× 爆傷並削減 50 耐力 | **RETUNED** | 消耗「滿層裂痕」→ 消耗裂痕標記觸發地震爆傷；現行：ESSBElem2.OnEarthHit；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **厚土**：岩甲上限 5 → 10 | DLL N4 | `ESSB_P_earth_0_1_B2` 0x0020B9 | 厚土：岩甲上限 5 → 10 | **SAME** | 現行：ESSBElem2.RockCap → ESSBController.AddSelf(2)；Papyrus 直讀：ESSBElem2×1 |
|  | 專精 | 主線 | 命中削減目標耐力 +0.5／點 | DLL N2 | `ESSB_P_earth_0_2_M1..M15` 0x0042C1–0x0042CF | 命中削減目標耐力 +0.5／點 | **SAME** | 現行：ESSBElem2.OnEarthHit；**DLL：kEarthStaminaCut** |
|  |  | 分支 1 | **汲力**：命中削減的耐力一半轉為你的耐力 | DLL N2 | `ESSB_P_earth_0_2_B1` 0x0020BC | 汲力：命中削減的耐力一半轉為你的耐力 | **SAME** | 現行：ESSBElem2.OnEarthHit；**DLL：kEarthDrainStrength** |
|  | 大師 | 主線 | 同調每段土附傷 +1%／點 | DLL N2 | `ESSB_P_earth_0_3_M1..M15` 0x0042D0–0x0042DE | 同調每段土附傷 +1%／點 | **SAME** | 現行：ESSBElem2.EarthHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcMaster[elem]** |
|  |  | 分支 1 | **不動**：岩甲 ≥5 時免疫擊退（自有） | 引擎效果 | `ESSB_P_earth_0_3_B1` 0x0020C0 | 不動：岩甲 ≥5 時免疫擊退（自有） | **SAME** | 現行：PERK ESSB_P_earth_0_3_B1 進入點 0x21（受到的擊退幅度）；ESP 進入點：0x21 |
|  |  | 分支 2 | **反震**：岩甲滿層時被近戰命中反震一次土傷並使攻擊者跌倒，每 10 秒一次，清空岩甲 | DLL 受擊 N4（跌倒推力：`AIProcess::KnockExplosion`） | `ESSB_P_earth_0_3_B2` 0x0020C1 | 反震：岩甲滿層時被近戰命中反震一次土傷並使攻擊者跌倒，每 10 秒一次，清空岩甲 | **SAME** | 現行：ESSBElem2.OnEarthRetaliate ← ESSBGuard.OnHitEx；Papyrus 直讀：ESSBElem2×1 |
|  | 傳奇 | 主線 | 地動，同調三段時重擊對耐力低於 30% 的目標跌倒，機率 5%／點 | DLL N4（跌倒推力：`AIProcess::KnockExplosion`） | `ESSB_P_earth_0_4_M1..M15` 0x0042DF–0x0042ED | 地動：同調三段時重擊對耐力低於 30% 的目標跌倒，機率 5%／點 | **SAME** | 現行：ESSBElem2.OnEarthHit → ESSBController.Knockdown；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **山岳**：同調三段時岩甲不因被打減少，物理減傷每層 +4% → +5%（合計上限仍 60%） | DLL 受擊 N4＋引擎效果 | `ESSB_P_earth_0_4_B1` 0x0020C4 | 山岳：同調三段時岩甲不因被打減少，物理減傷每層 +1% → +3% | **RETUNED** | 物理減傷每層 +1→+3% 改為 +4→+5%（基礎 1%／層 → 4%／層，ESSB_P_BaseRules 也要改）；現行：ESSBGuard.OnHitEx + PERK ESSB_P_earth_0_4_B1 進入點 0x24 ×5 段；ESP 進入點：0x24×5 |
| 開啟（地臨） | 新手 | 主線 | 開印岩甲 +1／每 5 點 | DLL N4 | `ESSB_P_earth_1_0_M1..M15` 0x0042EE–0x0042FC | 開印岩甲 +1／每 5 點 | **SAME** | 現行：ESSBElem2.OpenStacks(4)；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **震波**：開印時附近 1 人也裂痕 | DLL N3（掃描 N5） | `ESSB_P_earth_1_0_B1` 0x0020C8 | 震波：開印時附近 1 人也裂痕 | **SAME** | 現行：ESSBElem2.OpenEarth；Papyrus 直讀：ESSBElem2×1 |
|  | 熟練 | 主線 | 開印後 5 秒內土附傷 +1%／點 | DLL N3 | `ESSB_P_earth_1_1_M1..M15` 0x0042FD–0x00430B | 開印後 5 秒內土附傷 +1%／點 | **SAME** | 現行：ESSBElem2.EarthHitMult（GetOpenBoost(4)）；Papyrus 直讀：ESSBElem2×1；Papyrus 共用：ESSBController.DifferencePossible／開印加成 |
|  |  | 分支 1 | **深裂痕**：開印時目標耐力低於 50% 則立即跌倒（掛倒地） | DLL N3（跌倒推力：`AIProcess::KnockExplosion`） | `ESSB_P_earth_1_1_B1` 0x0020CC | 深裂痕：開印那一擊附傷 ×1.5 | **CHANGED** | 開印 ×1.5 → 耐力 <50% 立即跌倒；現行：ESSBElem.OpenStrikeMult → ESSBController.ApplyProc；Papyrus 共用：ESSBElem.OpenStrikeMult ×1.5＋ESSBController.DifferencePossible（各元素共用） |
|  |  | 分支 2 | **岩膚**：開印時你 +2 → +4 岩甲 | DLL N4 | `ESSB_P_earth_1_1_B2` 0x0020CD | 岩膚：開印時你 +2 → +4 岩甲 | **SAME** | 現行：ESSBElem2.OpenStacks(4)；Papyrus 直讀：ESSBElem2×1 |
|  | 專精 | 主線 | 土印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_earth_1_2_M1..M15` 0x00430C–0x00431A | 土印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBElem.MarkDurationBonus → ESSBController.ApplyMark；Papyrus 共用：ESSBElem.MarkDurationBonus |
|  |  | 分支 1 | **地臨強化**：地臨時岩甲滿層（開場就能碎岩），範圍內敵人耐力 -50% | Papyrus＋DLL N4／N5 | `ESSB_P_earth_1_2_B1` 0x0020D0 | 地臨強化：地臨時岩甲滿層，範圍內敵人減速 30% 3 秒 | **CHANGED** | 範圍減速 30% → 範圍耐力 -50%（減速分支只留冰）；現行：ESSBElem2.OnFormOpened(4)；Papyrus 直讀：ESSBElem2×1 |
|  | 大師 | 主線 | 地臨，開土形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | Papyrus＋DLL N5 | `ESSB_P_earth_1_3_M1..M15` 0x00431B–0x004329 | 地臨：開土形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem.OnFormOpened → ESSBController.ForceOpenOn；Papyrus 共用：ESSBElem.OnFormOpened（X 臨） |
|  |  | 分支 1 | **地基**：開印目標 3 秒內耐力不回復（自有效果把耐力回復設 0） | DLL N3＋引擎效果 | `ESSB_P_earth_1_3_B1` 0x0020D4 | 地基：開印目標 3 秒內移速 -30% | **CHANGED** | 移速 -30% → 耐力不回復；現行：ESSBElem2.OpenEarth；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **裂地**：開印目標 8 秒內若被土弄倒，倒地標記 3 → 5 秒 | DLL N3 | `ESSB_P_earth_1_3_B2` 0x0020D5 | 裂地：開印在目標腳下留 3 秒減速地帶 | **CHANGED** | 減速地帶 → 倒地標記延長；現行：ESSBElem2.OpenEarth → ESSBController.StartDomain(4, 3)；Papyrus 直讀：ESSBElem2×1 |
|  | 傳奇 | 主線 | 開印效果 +3%／點 | DLL N3 | `ESSB_P_earth_1_4_M1..M15` 0x00432A–0x004338 | 開印效果 +3%／點 | **SAME** | 現行：ESSBElem.OpenMult；Papyrus 共用：ESSBElem.OpenMult |
|  |  | 分支 1 | **先震**：同調三段時開印立即一次 ×0.5 地震，不含跌倒 | DLL N5 | `ESSB_P_earth_1_4_B1` 0x0020D8 | 先震：同調三段時開印立即一次 ×0.5 地震，不含跌倒 | **SAME** | 現行：ESSBElem2.OpenEarth → Quake(0.5, abKnock = False)；Papyrus 直讀：ESSBElem2×1 |
| 關閉（地震） | 新手 | 主線 | 終焉 +2%／點 | DLL N3（融斷 N5） | `ESSB_P_earth_2_0_M1..M15` 0x004339–0x004347 | 終焉 +2%／點 | **SAME** | 現行：ESSBElem.EndMult；Papyrus 共用：ESSBElem.EndMult |
|  |  | 分支 1 | **崩裂**：地震 ×1.5 → ×2.0 | DLL N5 | `ESSB_P_earth_2_0_B1` 0x0020DC | 崩裂：地震 ×1.5 → ×2.0 | **SAME** | 現行：ESSBElem2.QuakeK；Papyrus 直讀：ESSBElem2×1 |
|  | 熟練 | 主線 | 土印記的融斷 +2%／點 | DLL N5 | `ESSB_P_earth_2_1_M1..M15` 0x004348–0x004356 | 土印記的融斷 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **廣震**：地震範圍 3 → 5 公尺 | DLL N5 | `ESSB_P_earth_2_1_B1` 0x0020E0 | 廣震：地震範圍 3 → 5 公尺 | **SAME** | 現行：ESSBElem2.QuakeRadius；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **固土**：土終焉後你岩甲滿層 | DLL N4 | `ESSB_P_earth_2_1_B2` 0x0020E1 | 固土：土終焉後你岩甲滿層 | **SAME** | 現行：ESSBElem2.EndEarthNodes → ESSBController.SetSelf(2)；Papyrus 直讀：ESSBElem2×1 |
|  | 專精 | 主線 | 地震耐力削減 +3%／點（不吃節點倍率） | DLL N5 | `ESSB_P_earth_2_2_M1..M15` 0x004357–0x004365 | 地震耐力削減 +3%／點 | **SAME** | v0.4 只補充說明；現行：ESSBElem2.QuakeStamina；Papyrus 直讀：ESSBElem2×1；Papyrus 共用：ESSBElem（SetEndBoost，任何樹這格有點數都會觸發） |
|  |  | 分支 1 | **地斷**：土印記融斷時，範圍內耐力低於 30% 的目標直接跌倒（掛倒地） | DLL N5（`AIProcess::KnockExplosion`） | `ESSB_P_earth_2_2_B1` 0x0020E4 | 地斷：土印記融斷附帶 3 秒泥沼，內部減速 40% | **CHANGED** | 泥沼減速 → 耐力 <30% 直接跌倒；現行：ESSBElem2.EndEarthNodes → StartDomain(4, 3)；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **蓄能**：消耗全部蓄勁，格擋觸發時換算每點蓄勁物理減傷 +1%（持續 3 秒）；重擊觸發時換算每點蓄勁下一次地震／碎岩傷害 +5%（可調） | DLL 受擊 N4；DLL N4 | （無） | — | **NEW** | 消耗蓄勁換減傷或地震傷害（依賴新基礎機制「蓄勁」）；— |
|  | 大師 | 主線 | 土印記的融斷再 +2%／點 | DLL N5 | `ESSB_P_earth_2_3_M1..M15` 0x004366–0x004374 | 土印記的融斷再 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **山崩**：土終焉對範圍內所有帶裂痕的目標各一次地震 | DLL N5 | `ESSB_P_earth_2_3_B1` 0x0020E8 | 山崩：土終焉對範圍內所有帶裂痕的目標各一次地震 | **SAME** | 現行：ESSBElem2.EndEarthNodes；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **塵暴**：地震使範圍內敵人攻擊 -20% 3 秒 | DLL N5 | `ESSB_P_earth_2_3_B2` 0x0020E9 | 塵暴：地震使範圍內敵人攻擊 -20% 3 秒 | **SAME** | 現行：ESSBElem2.QuakeOne；Papyrus 直讀：ESSBElem2×1 |
|  | 傳奇 | 主線 | 地震 +3%／點 | DLL N3（融斷 N5） | `ESSB_P_earth_2_4_M1..M15` 0x004375–0x004383 | 地震 +3%／點 | **SAME** | 現行：ESSBElem.SignatureMult → ESSBElem2.Quake；Papyrus 共用：ESSBElem.SignatureMult |
|  |  | 分支 1 | **地裂**：土印記融斷後留下 5 秒地裂帶，內部敵人耐力不回復，耐力歸 0 的敵人在其中跌倒（每目標 8 秒一次，掛倒地） | Papyrus（領域與推力） | `ESSB_P_earth_2_4_B1` 0x0020EC | 地裂：土印記融斷後留下 5 秒地裂帶，內部敵人減速 50%、耐力不回復 | **CHANGED** | 拿掉減速 50%，加上耐力歸 0 跌倒；現行：ESSBElem2.EndEarthNodes → ESSBController.TickDomain；Papyrus 直讀：ESSBController×1、ESSBElem2×1 |

### 5.7 風（`wind`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續（連斬） | 新手 | 主線 | 風刃傷害 +2%／點 | DLL N4 | `ESSB_P_wind_0_0_M1..M15` 0x004384–0x004392 | 風刃傷害 +2%／點 | **SAME** | 現行：ESSBElem2.WindBladeMult；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **迴旋**：風刃改為對附近 2 人各一段 | DLL N5 | `ESSB_P_wind_0_0_B1` 0x0020F0 | 迴旋：風刃改為對附近 2 人各一段 | **SAME** | 現行：ESSBElem2.WindBlade；Papyrus 直讀：ESSBElem2×1 |
|  | 熟練 | 主線 | 風附傷 +1%／點 | DLL N2 | `ESSB_P_wind_0_1_M1..M15` 0x004393–0x0043A1 | 風附傷 +1%／點 | **SAME** | 現行：ESSBElem2.WindHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcAdept[elem]** |
|  |  | 分支 1 | **亂舞**：風勢門檻 4 → 3 | DLL N4 | `ESSB_P_wind_0_1_B1` 0x0020F4 | 亂舞：風勢門檻 4 → 3 | **SAME** | 現行：ESSBElem2.WindThreshold；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **順風**：命中回復耐力 5 | DLL N2 | `ESSB_P_wind_0_1_B2` 0x0020F5 | 順風：命中回復耐力 5 | **SAME** | 現行：ESSBElem2.OnWindHit；**DLL：kWindTailwind** |
|  | 專精 | 主線 | 風形態移速再 +0.5%／點（+10% → +17.5%） | Papyrus | `ESSB_P_wind_0_2_M1..M15` 0x0043A2–0x0043B0 | 風形態移速再 +0.5%／點（+10% → +17.5%） | **SAME** | 現行：ESSBElem2.WindSpeedBonus → ESSBController.RefreshWindAbiliti…；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **追風**：風刃命中回復耐力 3，並讓目標失衡 | DLL N4 | `ESSB_P_wind_0_2_B1` 0x0020F8 | 追風：風刃命中回復耐力 3，並讓目標失衡 | **SAME** | 現行：ESSBElem2.WindBladeOne；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **無聲**：潛行中風形態完全無聲（Muffle 1.0），潛行移速 +20% | Papyrus | `ESSB_P_wind_0_2_B2` 0x0020F9 | 無聲：潛行中風形態完全無聲（Muffle 1.0），潛行移速 +20% | **SAME** | 現行：SPEL ESSB_SilentAbility + ESSBController.RefreshWindStealth；Papyrus 直讀：ESSBElem2×1 |
|  | 大師 | 主線 | 同調每段風附傷 +1%／點 | DLL N2 | `ESSB_P_wind_0_3_M1..M15` 0x0043B1–0x0043BF | 同調每段風附傷 +1%／點 | **SAME** | 現行：ESSBElem2.WindHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcMaster[elem]** |
|  |  | 分支 1 | **殘影**：風勢滿時被近戰命中 30% 機率讓下一次攻擊無效（消耗風勢） | DLL 受擊 N4 | `ESSB_P_wind_0_3_B1` 0x0020FC | 殘影：風勢滿時被近戰命中 30% 機率無效化，消耗風勢 | **RETUNED** | 措辭：讓下一次攻擊無效；現行：ESSBGuard.OnHitEx + PERK ESSB_P_wind_0_3_B1 進入點 0x24 ×0；ESP 進入點：0x24 |
|  |  | 分支 2 | **疾風**：移速再 +10%，衝刺時每秒回補耐力再加倍（合計約當消耗的 50%，可調；找不到能直接調低耗量的進入點，改用回補） | Papyrus | `ESSB_P_wind_0_3_B2` 0x0020FD | 疾風：移速再 +10%，衝刺耐力消耗 -50% | **RETUNED** | 衝刺耗耐 -50% 改用每秒回補（找不到降耗進入點）；現行：ESSBElem2.WindSpeedBonus；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 3 | **暗風**：潛行攻擊的風附傷 ×3 → ×5，潛行攻擊送出的風刃 ×2 | DLL N4 | `ESSB_P_wind_0_3_B3` 0x0020FE | 暗風：潛行攻擊的風附傷 ×3 → ×5，潛行攻擊送出的風刃 ×2 | **SAME** | 現行：ESSBElem2.SneakMult / WindBladeMult；Papyrus 直讀：ESSBController×1、ESSBElem2×2 |
|  | 傳奇 | 主線 | 千刃，同調三段時每次命中附帶風刃，機率 5%／點 | DLL N4 | `ESSB_P_wind_0_4_M1..M15` 0x0043C0–0x0043CE | 千刃：同調三段時每次命中附帶風刃，機率 5%／點 | **SAME** | 現行：ESSBElem2.OnWindHit；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **御風**：同調三段時免疫減速（自有），且失衡目標受你**所有**傷害 +30%（含武器傷害） | 引擎效果 | `ESSB_P_wind_0_4_B1` 0x002100 | 御風：同調三段時免疫減速（自有），且失衡目標受你所有傷害 +30% | **SAME** | v0.4 只補充說明；現行：ESSBElem2.WindSlowImmune → ESSBNodes.SelfSlowImmune；ESSBElem…；Papyrus 直讀：ESSBController×1、ESSBElem2×2 |
| 開啟（風臨） | 新手 | 主線 | 開印風勢 +1／每 5 點 | DLL N4 | `ESSB_P_wind_1_0_M1..M15` 0x0043CF–0x0043DD | 開印風勢 +1／每 5 點 | **SAME** | 現行：ESSBElem2.OpenStacks(5)；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **風襲**：開印時附近 1 人也風痕 | DLL N3（掃描 N5） | `ESSB_P_wind_1_0_B1` 0x002104 | 風襲：開印時附近 1 人也風痕 | **SAME** | 現行：ESSBElem2.OpenWind；Papyrus 直讀：ESSBElem2×1 |
|  | 熟練 | 主線 | 開印拉近距離 +0.1 公尺／點（1.5 → 3 公尺） | Papyrus（推力） | `ESSB_P_wind_1_1_M1..M15` 0x0043DE–0x0043EC | 開印拉近距離 +0.1 公尺／點（1.5 → 3 公尺） | **SAME** | 現行：ESSBElem2.PullDistance → ESSBController.PullIn；Papyrus 直讀：ESSBElem2×1；Papyrus 共用：ESSBController.DifferencePossible／開印加成 |
|  |  | 分支 1 | **疾風痕**：開印風勢直接滿 | DLL N4 | `ESSB_P_wind_1_1_B1` 0x002108 | 疾風痕：開印風勢直接滿 | **SAME** | 現行：ESSBElem2.OpenStacks(5)；Papyrus 直讀：ESSBElem2×1；Papyrus 共用：ESSBElem.OpenStrikeMult ×1.5＋ESSBController.DifferencePossible（各元素共用） |
|  |  | 分支 2 | **輕躍**：開印後 3 秒移速 +10% | DLL N3 | `ESSB_P_wind_1_1_B2` 0x002109 | 輕躍：開印後 3 秒移速 +10% | **SAME** | 現行：ESSBElem2.OpenWind；Papyrus 直讀：ESSBElem2×1 |
|  | 專精 | 主線 | 風印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_wind_1_2_M1..M15` 0x0043ED–0x0043FB | 風印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBElem.MarkDurationBonus；Papyrus 共用：ESSBElem.MarkDurationBonus |
|  |  | 分支 1 | **氣旋**：風臨時把範圍內敵人拉到你面前 2 公尺 | Papyrus | `ESSB_P_wind_1_2_B1` 0x00210C | 氣旋：風臨時把範圍內敵人拉到你面前 2 公尺 | **SAME** | 現行：ESSBElem2.OnFormOpened(5) → ESSBController.PullIn；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **奇襲**：潛行攻擊的開印同時觸發終焉（一刀開印兼吹飛），且不拉近 | DLL N3 | `ESSB_P_wind_1_2_B2` 0x00210D | 奇襲：潛行攻擊的開印同時觸發終焉（一刀開印兼吹飛），且不拉近 | **SAME** | 現行：ESSBElem2.OpenWind（ESSBController.LastHitWasSneak）；Papyrus 直讀：ESSBElem2×2 |
|  | 大師 | 主線 | 風臨，開風形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | Papyrus＋DLL N5 | `ESSB_P_wind_1_3_M1..M15` 0x0043FC–0x00440A | 風臨：開風形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem.OnFormOpened；Papyrus 共用：ESSBElem.OnFormOpened（X 臨） |
|  |  | 分支 1 | **牽引**：開印拉近時，目標身後 1.5 公尺內的其他敵人也一起被拉近並失衡（最多 2 人，各自 3 秒推力冷卻） | DLL N3（掃描 N5）＋Papyrus（推力） | `ESSB_P_wind_1_3_B1` 0x002110 | 牽引：拉近的目標 2 秒內無法後退（自有減速 80%） | **CHANGED** | 拉近目標無法後退（減速 80%）→ 身後敵人一起拉近並失衡；現行：ESSBController.PullTo；Papyrus 直讀：ESSBController×1 |
|  |  | 分支 2 | **氣流**：開印時回復 10 耐力 | DLL N3 | `ESSB_P_wind_1_3_B2` 0x002111 | 氣流：開印時回復 10 耐力 | **SAME** | 現行：ESSBElem2.OpenWind；Papyrus 直讀：ESSBElem2×1 |
|  | 傳奇 | 主線 | 開印效果 +3%／點 | DLL N3 | `ESSB_P_wind_1_4_M1..M15` 0x00440B–0x004419 | 開印效果 +3%／點 | **SAME** | 現行：ESSBElem.OpenMult；Papyrus 共用：ESSBElem.OpenMult |
|  |  | 分支 1 | **先風**：同調三段時開印附帶一段風刃 | DLL N4 | `ESSB_P_wind_1_4_B1` 0x002114 | 先風：同調三段時開印附帶一段風刃 | **SAME** | 現行：ESSBElem2.OpenWind；Papyrus 直讀：ESSBElem2×1 |
| 關閉（吹飛） | 新手 | 主線 | 終焉 +2%／點 | DLL N3（融斷 N5） | `ESSB_P_wind_2_0_M1..M15` 0x00441A–0x004428 | 終焉 +2%／點 | **SAME** | 現行：ESSBElem.EndMult；Papyrus 共用：ESSBElem.EndMult |
|  |  | 分支 1 | **亂流**：風刃附近目標 2 → 5 人 | DLL N5 | `ESSB_P_wind_2_0_B1` 0x002118 | 亂流：風刃附近目標 2 → 5 人 | **SAME** | 現行：ESSBReactions.EndWind；Papyrus 直讀：ESSBReactions×1 |
|  | 熟練 | 主線 | 風印記的融斷 +2%／點 | DLL N5 | `ESSB_P_wind_2_1_M1..M15` 0x004429–0x004437 | 風印記的融斷 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **上天**：終焉的吹飛改為吹上天，落地時受 B_max ×1.0 風傷 | DLL N3／N5＋Papyrus（推力） | `ESSB_P_wind_2_1_B1` 0x00211C | 上天：終焉的吹飛改為吹上天，落地時受 B_max ×1.0 風傷 | **SAME** | 現行：ESSBElem2.BlowAway → ESSBController.LiftUp → ESSBStatus 浮空；Papyrus 直讀：ESSBElem2×2 |
|  |  | 分支 2 | **風斷**：風印記融斷時每個目標各兩段風刃 | DLL N5 | `ESSB_P_wind_2_1_B2` 0x00211D | 風斷：風印記融斷時每個目標各兩段風刃 | **SAME** | 現行：ESSBElem2.EndWindNodes；Papyrus 直讀：ESSBElem2×1 |
|  | 專精 | 主線 | 多段觸發，風印記被切掉時接管元素的命中觸發次數 +1／每 5 點（2 → 最多 5） | DLL N4 | `ESSB_P_wind_2_2_M1..M15` 0x004438–0x004446 | 吹飛距離 +0.2 公尺／點（3 → 6 公尺） | **CHANGED** | 吹飛距離 → 多段觸發次數（風的新核心機制）；現行：ESSBElem2.BlowDistance；Papyrus 直讀：ESSBElem2×1；Papyrus 共用：ESSBElem（SetEndBoost，任何樹這格有點數都會觸發） |
|  |  | 分支 1 | **風渦**：終焉時 5 公尺內敵人被拉向目標聚攏 | DLL N5＋Papyrus（推力） | `ESSB_P_wind_2_2_B1` 0x002120 | 風渦：終焉時 5 公尺內敵人被拉向目標聚攏（物理推力，需實測） | **SAME** | 拿掉「需實測」註記；現行：ESSBElem2.EndWindNodes → ESSBController.PullTo；Papyrus 直讀：ESSBElem2×1 |
|  | 大師 | 主線 | 風印記的融斷再 +2%／點 | DLL N5 | `ESSB_P_wind_2_3_M1..M15` 0x004447–0x004455 | 風印記的融斷再 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **颶風**：融斷的吹上天改為對範圍內所有敵人，不限帶風印記 | DLL N5＋Papyrus | `ESSB_P_wind_2_3_B1` 0x002124 | 颶風：融斷的吹上天改為對範圍內所有敵人，不限帶風印記 | **SAME** | 現行：ESSBElem2.EndWindNodes；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **順勢**：風終焉後 5 秒內接管元素的命中皆附帶一段風刃 | DLL N4 | `ESSB_P_wind_2_3_B2` 0x002125 | 順勢：風終焉後 5 秒內接管元素的命中皆附帶一段風刃 | **SAME** | 現行：ESSBController.SetWindFollow → OnWeaponHit；Papyrus 直讀：ESSBElem2×1 |
|  | 傳奇 | 主線 | 落地傷害 +5%／點（×0.5 → ×1.25） | DLL N3 | `ESSB_P_wind_2_4_M1..M15` 0x004456–0x004464 | 落地傷害 +5%／點（×0.5 → ×1.25） | **SAME** | 現行：ESSBElem2.LandingDamage；Papyrus 直讀：ESSBElem2×1；Papyrus 共用：ESSBElem.SignatureMult |
|  |  | 分支 1 | **空中追擊**：浮空目標受你的**所有**傷害 ×1.5（含武器傷害），風刃命中空中目標再推高 1 公尺並延長滯空 | 引擎效果＋DLL N4＋Papyrus（推力） | `ESSB_P_wind_2_4_B1` 0x002128 | 空中追擊：被吹飛或吹上天的敵人落地前受你的所有傷害 ×1.5，風刃命中空中目標再推高 1 公尺並延長滯空 | **RETUNED** | 條件改為「浮空」自有狀態，明寫含武器傷害；現行：ESSBElem2.TargetDamageMult / WindBladeOne；Papyrus 直讀：ESSBController×1、ESSBElem2×2 |
|  |  | 分支 2 | **連殺**：帶風印記的目標被你的潛行攻擊殺死後 5 秒內不解除潛行，下一次潛行攻擊附傷 ×2 並重置奇襲 | DLL N5＋Papyrus | `ESSB_P_wind_2_4_B2` 0x002129 | 連殺：潛行攻擊擊殺後 5 秒內不解除潛行，下一次潛行攻擊附傷 ×2 並重置奇襲 | **RETUNED** | 加上「帶風印記」條件；現行：ESSBElem2.OnKill → ESSBController.KeepSneak / TakeKillStreak；Papyrus 直讀：ESSBController×1、ESSBElem2×2 |

### 5.8 鮮血（`blood`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續（血位） | 新手 | 主線 | 流血每層傷害 +2%／點，放血係數 +0.01%／點（0.3% → 0.45%，不吃節點倍率） | DLL N3 | `ESSB_P_blood_0_0_M1..M15` 0x004465–0x004473 | 流血每層傷害 +2%／點，放血係數 +0.01%／點（0.3% → 0.45%） | **SAME** | 明寫放血係數不吃節點倍率（現行 fix8 已是如此）；現行：ESSBElem2.BleedTickMult / BleedDrainPercent → ESSBStatus.Tic…；Papyrus 直讀：ESSBElem2×2 |
|  |  | 分支 1 | **血刃**：重擊扣掉的生命，50% 加進這一擊的血附傷（扣越多砍越重） | DLL N4 | （無） | — | **NEW** | 重擊扣的生命 50% 加進血附傷；— |
|  |  | 分支 2 | **深創**：血痕上限 8 → 12 | DLL N3 | `ESSB_P_blood_0_0_B2` 0x00212D | 深創：血痕上限 8 → 12 | **SAME** | 現行：ESSBElem2.BleedCap → ESSBController.StackCap(5)；Papyrus 直讀：ESSBElem2×1 |
|  |  | （移除） | — | — | `ESSB_P_blood_0_0_B1` 0x00212C | 血氣：維持扣血與重擊扣血減半 | **REMOVED** | 「不再有取消扣血的節點」；現行：ESSBController.BloodCostScale；Papyrus 直讀：ESSBController×1 |
|  | 熟練 | 主線 | 血附傷 +1%／點 | DLL N2 | `ESSB_P_blood_0_1_M1..M15` 0x004474–0x004482 | 血附傷 +1%／點 | **SAME** | 現行：ESSBElem2.BloodHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcAdept[elem]** |
|  |  | 分支 1 | **飲血**：擊殺流血目標時回血 20%，並獲得 10 秒「嗜血」：命中效果 +20%、吸血 +10%，不受血位影響 | DLL N5 | `ESSB_P_blood_0_1_B1` 0x002130 | 飲血：擊殺流血目標時回血 20%，並獲得 10 秒「嗜血」：命中效果 +20%、吸血 +10%，不受血位影響 | **SAME** | 現行：ESSBElem2.OnKill ← ESSBGuard.OnActorKilled + PERK ESSB_P_blo…；Papyrus 直讀：ESSBElem2×1；ESP 進入點：0x23 |
|  |  | 分支 2 | **血溢**：生命已滿時吸血溢出的量不浪費，灌進護血（上限最大生命 20%，隨節點擴充） | DLL N2 | `ESSB_P_blood_0_1_B2` 0x002131 | 血盾：吸血溢出轉為臨時護盾，上限 20% 生命 | **RETUNED** | 改名；臨時生命 AV（TempHealth）→ 護血池（自有效果強度，N2 正在接）；現行：ESSBController.Leech（ESSB_Util_TempHealth）；**DLL：kBloodOverflow** |
|  | 專精 | 主線 | 吸血比例各血位 +1%／點 | DLL N2 | `ESSB_P_blood_0_2_M1..M15` 0x004483–0x004491 | 吸血比例各血位 +1%／點 | **SAME** | 現行：ESSBController.GetBloodLeechRatio；Papyrus 直讀：ESSBController×1；**DLL：kBloodLeechRatio** |
|  |  | 分支 1 | **逆流**：反轉血位曲線，低血位命中強、高血位吸血強，損血曲線不變 | DLL N2 | `ESSB_P_blood_0_2_B1` 0x002134 | 逆流：反轉血位曲線，低血位命中強、高血位吸血強，損血曲線不變 | **SAME** | 現行：ESSBController.BloodPercent；Papyrus 直讀：ESSBController×2；**DLL：kBloodReverse** |
|  |  | 分支 2 | **血承**：擊殺流血目標時吸收其屬性 15 秒：其火、冰、雷、毒、魔抗各 50%、護甲 20%、最大生命 10%；只保留最近一個 | DLL N5 | `ESSB_P_blood_0_2_B2` 0x002135 | 血承：擊殺流血目標時吸收其屬性 15 秒：其火、冰、雷、毒、魔抗各 50%、護甲 20%、最大生命 10%；只保留最近一個 | **SAME** | 現行：ESSBController.ApplyInherit（SPEL ESSB_InheritSpell，7 個 Peak …；Papyrus 直讀：ESSBElem2×1 |
|  | 大師 | 主線 | 同調每段血附傷 +1%／點 | DLL N2 | `ESSB_P_blood_0_3_M1..M15` 0x004492–0x0044A0 | 同調每段血附傷 +1%／點 | **SAME** | 現行：ESSBElem2.BloodHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcMaster[elem]** |
|  |  | 分支 1 | **止血**：低血位（30% 以下）時流血目標的流血傷害 ×1.5，於套用血痕當下依你目前血位寫入強度 | DLL N3 | `ESSB_P_blood_0_3_B1` 0x002138 | 止血：低血位（30% 以下）時流血目標的流血傷害 ×1.5 | **SAME** | v0.4 只補充說明；現行：ESSBElem2.BleedTickMult；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **血怒**：中血位（30～70%）時命中效果與吸血同時 +15% | DLL N2 | `ESSB_P_blood_0_3_B2` 0x002139 | 血怒：中血位（30～70%）時命中效果與吸血同時 +15% | **SAME** | 現行：ESSBController.GetBloodHitMult / GetBloodLeechRatio；Papyrus 直讀：ESSBController×3；**DLL：kBloodRage** |
|  | 傳奇 | 主線 | 血海，同調三段時血潮改為範圍，範圍 1 公尺 +0.2 公尺／點 | DLL N5 | `ESSB_P_blood_0_4_M1..M15` 0x0044A1–0x0044AF | 血海：同調三段時血潮改為範圍，範圍 1 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem2.SurgeRadius → ESSBReactions.EndBlood；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **不死**：同調三段時流血目標死亡，你回滿耐力，並回復生命到剛好越過上方最近的一條線（30% 或 70%），觸發一次回湧（不受越線冷卻，每 30 秒一次） | DLL N5 | `ESSB_P_blood_0_4_B1` 0x00213C | 不死：同調三段時維持扣血歸零，流血目標死亡時你回滿耐力 | **CHANGED** | 維持扣血歸零 → 回血越線＋回湧；現行：ESSBController.BloodCostScale / ESSBElem2.OnKill；Papyrus 直讀：ESSBController×1、ESSBElem2×1 |
| 開啟（血臨） | 新手 | 主線 | 開印流血 +1 層／每 5 點 | DLL N3 | `ESSB_P_blood_1_0_M1..M15` 0x0044B0–0x0044BE | 開印流血 +1 層／每 5 點 | **SAME** | 現行：ESSBElem2.OpenStacks(6)；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **血濺**：開印時附近 1 人流血 1 層 | DLL N3（掃描 N5） | `ESSB_P_blood_1_0_B1` 0x002140 | 血濺：開印時附近 1 人流血 1 層 | **SAME** | 現行：ESSBElem2.OpenBlood；Papyrus 直讀：ESSBElem2×1 |
|  | 熟練 | 主線 | 開印後 5 秒內血附傷 +1%／點 | DLL N3 | `ESSB_P_blood_1_1_M1..M15` 0x0044BF–0x0044CD | 開印後 5 秒內血附傷 +1%／點 | **SAME** | 現行：ESSBElem2.BloodHitMult；Papyrus 直讀：ESSBElem2×1；Papyrus 共用：ESSBController.DifferencePossible／開印加成 |
|  |  | 分支 1 | **深血痕**：開印依你的血區：高血區血痕多 +2 層、中血區多 +1 層並吸血一次、低血區吸血兩次 | DLL N3 | `ESSB_P_blood_1_1_B1` 0x002144 | 深血痕：開印那一擊附傷 ×1.5 | **CHANGED** | 開印 ×1.5 → 依血區加層或吸血；現行：ESSBElem.OpenStrikeMult；Papyrus 共用：ESSBElem.OpenStrikeMult ×1.5＋ESSBController.DifferencePossible（各元素共用） |
|  |  | 分支 2 | **開印回血**：開印時你回血 B_max ×0.5，低血位 ×2 | DLL N3 | `ESSB_P_blood_1_1_B2` 0x002145 | 開印回血：開印時你回血 B_max ×0.5，低血位 ×2 | **SAME** | 現行：ESSBElem2.OpenBlood；Papyrus 直讀：ESSBElem2×1 |
|  | 專精 | 主線 | 血印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_blood_1_2_M1..M15` 0x0044CE–0x0044DC | 血印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBElem.MarkDurationBonus；Papyrus 共用：ESSBElem.MarkDurationBonus |
|  |  | 分支 1 | **血臨強化**：血臨時你付最大生命 15%（代價路徑，留 1 點），並立即觸發一次濺血（不受越線冷卻） | Papyrus＋DLL N3（濺血 N5） | `ESSB_P_blood_1_2_B1` 0x002148 | 血臨強化：血臨後 10 秒不扣血 | **CHANGED** | 10 秒不扣血 → 付 15% 生命換濺血；現行：ESSBElem2.OnFormOpened(6) → ESSBController.SetNoBloodCost(10…；Papyrus 直讀：ESSBElem2×1 |
|  | 大師 | 主線 | 血臨，開血形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | Papyrus＋DLL N5 | `ESSB_P_blood_1_3_M1..M15` 0x0044DD–0x0044EB | 血臨：開血形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem.OnFormOpened；Papyrus 共用：ESSBElem.OnFormOpened（X 臨） |
|  |  | 分支 1 | **血咒**：開印目標 5 秒內生命回復速率 -50% | DLL N3 | `ESSB_P_blood_1_3_B1` 0x00214C | 血咒：開印目標 5 秒內受治療 -50% | **RETUNED** | 受治療 -50% → 生命回復速率 -50%（現行已用 AV 155）；現行：ESSBElem2.OpenBlood（ESSB_Util_HealRateDebuff）；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **血脈**：開印時 +2 同調 | DLL N4 | `ESSB_P_blood_1_3_B2` 0x00214D | 血脈：開印時 +2 同調 | **SAME** | 現行：ESSBElem2.OpenBlood；Papyrus 直讀：ESSBElem2×1 |
|  | 傳奇 | 主線 | 開印效果 +3%／點 | DLL N3 | `ESSB_P_blood_1_4_M1..M15` 0x0044EC–0x0044FA | 開印效果 +3%／點 | **SAME** | 現行：ESSBElem.OpenMult；Papyrus 共用：ESSBElem.OpenMult |
|  |  | 分支 1 | **血祭之始**：同調三段時開印立即結算一次 ×0.5 血潮 | DLL N3 | `ESSB_P_blood_1_4_B1` 0x002150 | 血祭之始：同調三段時開印立即結算一次 ×0.5 血潮 | **SAME** | 現行：ESSBElem2.OpenBlood；Papyrus 直讀：ESSBElem2×1 |
| 關閉（血潮） | 新手 | 主線 | 終焉 +2%／點 | DLL N3（融斷 N5） | `ESSB_P_blood_2_0_M1..M15` 0x0044FB–0x004509 | 終焉 +2%／點 | **SAME** | 現行：ESSBElem.EndMult；Papyrus 共用：ESSBElem.EndMult |
|  |  | 分支 1 | **飽飲**：血潮結算的流血傷害 ×1.5 | DLL N3 | `ESSB_P_blood_2_0_B1` 0x002154 | 飽飲：血潮結算的流血傷害 ×1.5 | **SAME** | 現行：ESSBReactions.EndBlood；Papyrus 直讀：ESSBReactions×1 |
|  | 熟練 | 主線 | 血印記的融斷 +2%／點 | DLL N5 | `ESSB_P_blood_2_1_M1..M15` 0x00450A–0x004518 | 血印記的融斷 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **血漫**：血潮結算時附近流血目標一起血潮 | DLL N5 | `ESSB_P_blood_2_1_B1` 0x002158 | 血漫：血潮結算時附近流血目標一起血潮 | **SAME** | 現行：ESSBElem2.EndBloodNodes；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **血斷**：血印記融斷治療你該傷害的 50% | DLL N5 | `ESSB_P_blood_2_1_B2` 0x002159 | 血斷：血印記融斷治療你該傷害的 50% | **SAME** | 現行：ESSBReactions.EndBlood → ESSBController.Leech；Papyrus 直讀：ESSBReactions×1 |
|  | 專精 | 主線 | 血潮治療倍率 ×2，每點 +0.1 | DLL N3 | `ESSB_P_blood_2_2_M1..M15` 0x004519–0x004527 | 血潮治療倍率 ×2 → 每點 +0.1 | **SAME** | 措辭；現行：ESSBElem2.SurgeHealMult；Papyrus 直讀：ESSBElem2×1；Papyrus 共用：ESSBElem（SetEndBoost，任何樹這格有點數都會觸發） |
|  |  | 分支 1 | **血約**：往上越線（回湧）時，15 公尺內所有流血目標血痕 +2 層 | DLL N3（掃描 N5） | `ESSB_P_blood_2_2_B1` 0x00215C | 血約：血終焉後 8 秒不扣血 | **CHANGED** | 8 秒不扣血 → 回湧時全場血痕 +2；現行：ESSBElem2.EndBloodNodes → ESSBController.SetNoBloodCost(8)；Papyrus 直讀：ESSBElem2×1 |
|  | 大師 | 主線 | 血印記的融斷再 +2%／點 | DLL N5 | `ESSB_P_blood_2_3_M1..M15` 0x004528–0x004536 | 血印記的融斷再 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **血契**：高血位（70% 以上）時血終焉損失 10% 生命，血潮 ×2 | DLL N3 | `ESSB_P_blood_2_3_B1` 0x002160 | 血契：高血位（70% 以上）時血終焉損失 10% 生命，血潮 ×2 | **SAME** | 現行：ESSBReactions.EndBlood → ESSBController.PayBloodCost；Papyrus 直讀：ESSBReactions×1 |
|  |  | 分支 2 | **放血終焉**：血潮的當前生命項 10% → 20%（首領 3% → 6%） | DLL N3 | `ESSB_P_blood_2_3_B2` 0x002161 | 放血終焉：血潮的當前生命項 10% → 20%（首領 3% → 6%） | **SAME** | 現行：ESSBElem2.SurgePercent；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 3 | **血引**：血終焉後接管元素的開印附帶流血 2 層 | DLL N3 | `ESSB_P_blood_2_3_B3` 0x002162 | 血引：血終焉後接管元素的開印附帶流血 2 層 | **SAME** | 現行：ESSBElem2.EndBloodNodes → ESSBController.SetPendingBleed(2)；Papyrus 直讀：ESSBElem2×1 |
|  | 傳奇 | 主線 | 血潮 +3%／點 | DLL N3（融斷 N5） | `ESSB_P_blood_2_4_M1..M15` 0x004537–0x004545 | 血潮 +3%／點 | **SAME** | 現行：ESSBElem.SignatureMult → ESSBReactions.EndBlood；Papyrus 共用：ESSBElem.SignatureMult |
|  |  | 分支 1 | **血池**：血印記融斷後留下 5 秒血池，你在其中每秒回血 | Papyrus（領域） | `ESSB_P_blood_2_4_B1` 0x002164 | 血池：血印記融斷後留下 5 秒血池，你在其中每秒回血 | **SAME** | 現行：ESSBElem2.EndBloodNodes → StartDomain(6) → ESSBController.Ti…；Papyrus 直讀：ESSBElem2×1 |

### 5.9 神聖（`divine`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續（聖佑） | 新手 | 主線 | 聖佑各階武器傷害與聖傷加成 +1%／點 × 階數（I 1、II 2、III 3） | 引擎效果 | `ESSB_P_divine_0_0_M1..M15` 0x004546–0x004554 | 聖印每層目標受聖傷 +1%／點 | **CHANGED** | 目標側聖印易傷 → 玩家側聖佑各階加成（引擎效果）；現行：ESSBElem2.HolyVulnerability；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **護持**：命中獲得 10% 魔抗 3 秒 | DLL N3 | `ESSB_P_divine_0_0_B1` 0x002168 | 護持：命中獲得 10% 魔抗 3 秒 | **SAME** | 現行：ESSBElem2.OnDivineHit；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **驅魔**：對死靈施法者傷害 +50% | DLL N2 | `ESSB_P_divine_0_0_B2` 0x002169 | 驅魔：對死靈施法者傷害 +50% | **SAME** | 現行：ESSBElem2.DivineHitMult → ESSBController.IsNecromancer；Papyrus 直讀：ESSBController×1；**DLL：kDivineExorcism** |
|  | 熟練 | 主線 | 聖附傷 +1%／點 | DLL N2 | `ESSB_P_divine_0_1_M1..M15` 0x004555–0x004563 | 聖附傷 +1%／點 | **SAME** | 現行：ESSBElem2.DivineHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcAdept[elem]** |
|  |  | 分支 1 | **神罰**：聖裁計數只要 2 擊（第二擊就觸發） | DLL N3 | `ESSB_P_divine_0_1_B1` 0x00216C | 神罰：聖印滿層時每次命中額外一次 50% 聖光 | **CHANGED** | 滿層額外聖光 → 聖裁計數只要 2 擊；現行：ESSBElem2.OnDivineHit；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **聖盾**：聖佑各階另給受法術傷害 -10%／-20%／-30% | 引擎效果 | `ESSB_P_divine_0_1_B2` 0x00216D | 聖盾：每命中 +1 層（最多 5），抵消魔法傷害 | **CHANGED** | 每命中疊層（PERK 0x29 ×5 段）→ 依聖佑階減法傷（PERK 條件改讀聖佑）；現行：ESSBElem2.OnDivineHit + PERK ESSB_P_divine_0_1_B2 進入點 0x29 ×…；Papyrus 直讀：ESSBController(GetBranch+SetNthEntryValue)×1、ESSBElem2×1；ESP 進入點：0x29×5 |
|  | 專精 | 主線 | 聖裁傷害 +2%／點 | DLL N3 | `ESSB_P_divine_0_2_M1..M15` 0x004564–0x004572 | 命中回血 +2%／點 | **CHANGED** | 命中回血 → 聖裁傷害；現行：ESSBElem2.OnDivineHit；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **光耀**：裁決後 3 公尺內的亡靈魔族 5 秒內受聖傷 +20% | DLL N5 | `ESSB_P_divine_0_2_B1` 0x002170 | 光耀：裁決後附近亡靈魔族減速 | **CHANGED** | 減速 → 受聖傷 +20%；現行：ESSBElem2.EndDivineNodes；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **聖灰**：敵人化為灰燼時你回復魔力 B_max ×2 | DLL N5 | `ESSB_P_divine_0_2_B2` 0x002171 | 聖灰：敵人化為灰燼時你回復魔力 B_max ×2 | **SAME** | 現行：ESSBElem2.OnAsh；Papyrus 直讀：ESSBElem2×1 |
|  | 大師 | 主線 | 同調每段聖附傷 +1%／點 | DLL N2 | `ESSB_P_divine_0_3_M1..M15` 0x004573–0x004581 | 同調每段聖附傷 +1%／點 | **SAME** | 現行：ESSBElem2.DivineHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcMaster[elem]** |
|  |  | 分支 1 | **破邪斬**：聖佑 III 時，聖裁對主目標造成的傷害另以 50% 濺到目標周圍 4 公尺內的其他敵人（最多 5 人，可調）；濺射只有傷害，不帶破防、不再觸發聖光爆，按接收者各自的抗性結算，對亡靈魔族 ×3 照算 | DLL N5 | （無） | — | **NEW** | 聖佑 III 聖裁濺射；— |
|  |  | 分支 2 | **庇護**：生命低於 30% 時聖佑直接 III 並刷新，每 30 秒一次 | DLL 受擊 N4 | `ESSB_P_divine_0_3_B2` 0x002175 | 庇護：生命低於 30% 時自動聖盾滿層，每 30 秒一次 | **CHANGED** | 聖盾滿層 → 聖佑直接 III；現行：ESSBElem2.OnTick → ESSBController.TakeSanctuary；Papyrus 直讀：ESSBElem2×1 |
|  |  | （移除） | — | — | `ESSB_P_divine_0_3_B1` 0x002174 | 祝福：命中時小範圍治療同伴 | **REMOVED** | 命中治療同伴；現行：ESSBElem2.HealAllies → ESSBController.ScanAllies；Papyrus 直讀：ESSBElem2×1 |
|  | 傳奇 | 主線 | 天啟，同調三段時裁決改為範圍，範圍 1 公尺 +0.2 公尺／點 | DLL N5 | `ESSB_P_divine_0_4_M1..M15` 0x004582–0x004590 | 天啟：同調三段時裁決改為範圍，範圍 1 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem2.JudgeArea；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **神佑**：同調三段時致命傷改為留 1 血並得到 2 秒無敵視窗，每場戰鬥一次（延遲死亡保護） | Papyrus | `ESSB_P_divine_0_4_B1` 0x002178 | 神佑：同調三段時致命傷改為留 1 血並清除所有負面，每場戰鬥一次 | **RETUNED** | 「清除負面」→「2 秒無敵」（現行實作已是無敵視窗）；現行：ESSBGuard.OnHitEx → TakeDivineSave + PERK ESSB_P_divine_0_4_…；Papyrus 直讀：ESSBController×2；ESP 進入點：0x24 |
|  |  | 分支 2 | **淨土**：同調三段時你在神聖形態中擊殺的所有敵人都化灰，不限是否帶印記 | DLL N5 | `ESSB_P_divine_0_4_B2` 0x002179 | 淨土：同調三段時你在神聖形態中擊殺的所有敵人都化灰，不限致命一擊是否神聖 | **RETUNED** | 措辭：不限是否帶印記；現行：ESSBElem2.ShouldAsh；Papyrus 直讀：ESSBElem2×1 |
| 開啟（聖臨） | 新手 | 主線 | 開印回血 +5%／點 | DLL N3 | `ESSB_P_divine_1_0_M1..M15` 0x004591–0x00459F | 開印回血 +5%／點 | **SAME** | 現行：ESSBElem2.OpenDivine；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 1 | **聖輝**：開印時附近 1 人也聖印 | DLL N3（掃描 N5） | `ESSB_P_divine_1_0_B1` 0x00217C | 聖輝：開印時附近 1 人也聖印 | **SAME** | 現行：ESSBElem2.OpenDivine；Papyrus 直讀：ESSBElem2×1 |
|  | 熟練 | 主線 | 開印後 5 秒內聖附傷 +1%／點 | DLL N3 | `ESSB_P_divine_1_1_M1..M15` 0x0045A0–0x0045AE | 開印後 5 秒內聖附傷 +1%／點 | **SAME** | 現行：ESSBElem2.DivineHitMult；Papyrus 直讀：ESSBElem2×1；Papyrus 共用：ESSBController.DifferencePossible／開印加成 |
|  |  | 分支 1 | **慈光**：開印時懲戒 +2（不需要聖佑 II） | DLL N3 | `ESSB_P_divine_1_1_B1` 0x002180 | 慈光：開印那一擊附傷 ×1.5 | **CHANGED** | 開印 ×1.5 → 懲戒 +2；現行：ESSBElem.OpenStrikeMult；Papyrus 共用：ESSBElem.OpenStrikeMult ×1.5＋ESSBController.DifferencePossible（各元素共用） |
|  |  | 分支 2 | **誓約**：開印的目標 8 秒內打你，懲戒每次 +2 而不是 +1（盯住一個敵人讓它打你） | DLL N3＋DLL 受擊 N4 | （無） | — | **NEW** | 開印目標打你時懲戒 +2；— |
|  |  | （移除） | — | — | `ESSB_P_divine_1_1_B2` 0x002181 | 聖護：開印時獲得 10% 魔抗 3 秒 | **REMOVED** | 開印魔抗 +10%；現行：ESSBElem2.OpenDivine；Papyrus 直讀：ESSBElem2×1 |
|  | 專精 | 主線 | 聖印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_divine_1_2_M1..M15` 0x0045AF–0x0045BD | 聖印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBElem.MarkDurationBonus；Papyrus 共用：ESSBElem.MarkDurationBonus |
|  |  | 分支 1 | **聖臨強化**：聖臨時你與附近同伴回血 B_max ×2 | Papyrus | `ESSB_P_divine_1_2_B1` 0x002184 | 聖臨強化：聖臨時你與附近同伴回血 B_max ×2 | **SAME** | 現行：ESSBElem2.OnFormOpened(7)；Papyrus 直讀：ESSBElem2×1 |
|  | 大師 | 主線 | 聖臨，開聖形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | Papyrus＋DLL N5 | `ESSB_P_divine_1_3_M1..M15` 0x0045BE–0x0045CC | 聖臨：開聖形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem.OnFormOpened；Papyrus 共用：ESSBElem.OnFormOpened（X 臨） |
|  |  | 分支 1 | **聖痕**：開印目標對亡靈魔族判定，非亡靈也受 +10% 聖傷 | DLL N3＋引擎效果 | `ESSB_P_divine_1_3_B1` 0x002188 | 聖痕：開印目標對亡靈魔族判定，非亡靈也受 +10% 聖傷 | **SAME** | 現行：ESSBElem2.IsHolyPrey / HolyVulnerability；Papyrus 直讀：ESSBElem2×2 |
|  |  | 分支 2 | **聖光**：開印時附近同伴回血 B_max | DLL N5 | `ESSB_P_divine_1_3_B2` 0x002189 | 聖光：開印時附近同伴回血 B_max | **SAME** | 現行：ESSBElem2.OpenDivine → HealAllies；Papyrus 直讀：ESSBElem2×1 |
|  | 傳奇 | 主線 | 開印效果 +3%／點 | DLL N3 | `ESSB_P_divine_1_4_M1..M15` 0x0045CD–0x0045DB | 開印效果 +3%／點 | **SAME** | 現行：ESSBElem.OpenMult；Papyrus 共用：ESSBElem.OpenMult |
|  |  | 分支 1 | **聖啟**：同調三段時開印讓聖佑直接升到 II | DLL N3 | `ESSB_P_divine_1_4_B1` 0x00218C | 聖啟：同調三段時開印對亡靈魔族立即一次 ×0.5 裁決 | **CHANGED** | 對亡靈 ×0.5 裁決 → 聖佑直接 II；現行：ESSBElem2.OpenDivine → Judge(0.5)；Papyrus 直讀：ESSBElem2×1 |
| 關閉（裁決） | 新手 | 主線 | 終焉 +2%／點 | DLL N3（融斷 N5） | `ESSB_P_divine_2_0_M1..M15` 0x0045DC–0x0045EA | 終焉 +2%／點 | **SAME** | 現行：ESSBElem.EndMult；Papyrus 共用：ESSBElem.EndMult |
|  |  | 分支 1 | **重裁**：裁決 ×2.0 → ×3.0 | DLL N3 | `ESSB_P_divine_2_0_B1` 0x002190 | 重裁：裁決 ×2.0 → ×3.0 | **SAME** | 現行：ESSBElem2.JudgeK；Papyrus 直讀：ESSBElem2×1 |
|  | 熟練 | 主線 | 聖印記的融斷 +2%／點 | DLL N5 | `ESSB_P_divine_2_1_M1..M15` 0x0045EB–0x0045F9 | 聖印記的融斷 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **廣裁**：裁決改為 3 公尺範圍 | DLL N5 | `ESSB_P_divine_2_1_B1` 0x002194 | 廣裁：裁決改為 3 公尺範圍 | **SAME** | 現行：ESSBElem2.JudgeArea；Papyrus 直讀：ESSBElem2×1 |
|  |  | 分支 2 | **聖斷**：聖印記融斷每個目標治療你 B_max ×1.0 | DLL N5 | `ESSB_P_divine_2_1_B2` 0x002195 | 聖斷：聖印記融斷每個目標治療你 B_max ×1.0 | **SAME** | 現行：ESSBElem2.EndDivineNodes；Papyrus 直讀：ESSBElem2×1 |
|  | 專精 | 主線 | 終焉後 5 秒內接管元素附傷 +1%／點 | DLL N3 | `ESSB_P_divine_2_2_M1..M15` 0x0045FA–0x004608 | 終焉後 5 秒內接管元素附傷 +1%／點 | **SAME** | 現行：ESSBElem.OnEnd → ESSBController.SetEndBoost / GetHitMult；Papyrus 共用：ESSBElem（SetEndBoost，任何樹這格有點數都會觸發） |
|  |  | 分支 1 | **聖域**：聖終焉後留下聖域 5 秒，其中敵人傷害 -20%，你持續回復 | Papyrus（領域） | `ESSB_P_divine_2_2_B1` 0x002198 | 聖域：聖終焉後留下聖域 5 秒，其中敵人傷害 -20%，你持續回復 | **SAME** | 現行：ESSBElem2.EndDivineNodes → StartDomain(7, 5) + PERK ESSB_P_d…；Papyrus 直讀：ESSBElem2×1；ESP 進入點：0x24 |
|  |  | 分支 2 | **淨灰**：帶神聖印記的亡靈化灰時爆出聖光，附近亡靈受 B_max ×1.0 聖傷 | DLL N5 | `ESSB_P_divine_2_2_B2` 0x002199 | 淨灰：裁決擊殺的亡靈化灰時爆出聖光，附近亡靈受 B_max ×1.0 聖傷 | **RETUNED** | 觸發條件：裁決擊殺 → 帶神聖印記化灰；現行：ESSBElem2.OnAsh；Papyrus 直讀：ESSBElem2×1 |
|  | 大師 | 主線 | 聖印記的融斷再 +2%／點 | DLL N5 | `ESSB_P_divine_2_3_M1..M15` 0x004609–0x004617 | 聖印記的融斷再 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **天誅**：懲戒上限 5 → 8；裁決消耗懲戒時，懲戒的加成部分另外對 3 公尺內其他敵人各結算一次（最多 5 人） | DLL 受擊 N4；DLL N5 | （無） | — | **NEW** | 懲戒上限 5→8＋懲戒加成範圍結算；— |
|  |  | 分支 2 | **聖引**：聖終焉後接管元素的開印治療你 B_max | DLL N3 | `ESSB_P_divine_2_3_B2` 0x00219D | 聖引：聖終焉後接管元素的開印治療你 B_max | **SAME** | 現行：ESSBElem2.EndDivineNodes → ESSBController.SetPendingHeal；Papyrus 直讀：ESSBElem2×1 |
|  |  | （移除） | — | — | `ESSB_P_divine_2_3_B1` 0x00219C | 處決：裁決處決範圍內低於 20% 生命的亡靈魔族 | **REMOVED** | 處決只在冰；現行：ESSBElem2.EndDivineNodes → ESSBController.Execute；Papyrus 直讀：ESSBElem2×1 |
|  | 傳奇 | 主線 | 裁決 +3%／點 | DLL N3（融斷 N5） | `ESSB_P_divine_2_4_M1..M15` 0x004618–0x004626 | 裁決 +3%／點 | **SAME** | 現行：ESSBElem.SignatureMult → ESSBElem2.Judge；Papyrus 共用：ESSBElem.SignatureMult |
|  |  | 分支 1 | **神聖領域**：聖印記融斷後留下 8 秒聖域；聖佑 III 時融斷不清空聖佑 | DLL N5＋Papyrus（領域） | `ESSB_P_divine_2_4_B1` 0x0021A0 | 神聖領域：聖印記融斷後留下 8 秒聖域 | **RETUNED** | 加上聖佑 III 融斷不清空；現行：ESSBElem2.EndDivineNodes → StartDomain(7, 8) + PERK ESSB_P_d…；Papyrus 直讀：ESSBElem2×1；ESP 進入點：0x24 |

### 5.10 毒素（`poison`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續（疫毒） | 新手 | 主線 | 每劑傷害 +2%／點 | DLL N3 | `ESSB_P_poison_0_0_M1..M15` 0x004627–0x004635 | 毒層每層傷害 +2%／點 | **RETUNED** | 毒層 → 劑（中毒改成單一效果）；現行：ESSBElem3.PoisonTickMult → ESSBStatus.Tick；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 1 | **免疫**：毒形態毒抗 +50% | Papyrus | `ESSB_P_poison_0_0_B1` 0x0021A4 | 免疫：毒形態毒抗 +50% | **SAME** | 現行：SPEL ESSB_Ability_PoisonResist + ESSBController.RefreshAbili…；Papyrus 直讀：ESSBElem3×1 |
|  | 熟練 | 主線 | 毒附傷 +1%／點 | DLL N2 | `ESSB_P_poison_0_1_M1..M15` 0x004636–0x004644 | 毒附傷 +1%／點 | **SAME** | 現行：ESSBElem3.PoisonHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcAdept[elem]** |
|  |  | 分支 1 | **萎靡**：目標中毒 ≥5 劑時攻擊 -15% | DLL N3 | `ESSB_P_poison_0_1_B1` 0x0021A8 | 衰弱：毒層 ≥5 時目標攻擊 -15% | **RETUNED** | 改名；毒層 → 劑；現行：ESSBElem3.OnPoisonHit；Papyrus 直讀：ESSBElem3×2 |
|  |  | 分支 2 | **毒皮**：被近戰命中時攻擊者中毒 +2 劑 | DLL 受擊 N4 | `ESSB_P_poison_0_1_B2` 0x0021A9 | 毒皮：被近戰命中時攻擊者 +2 毒層 | **RETUNED** | 毒層 → 劑；現行：ESSBGuard.OnHitEx → ESSBElem3.OnPoisonSkin；Papyrus 直讀：ESSBElem3×1 |
|  | 專精 | 主線 | 瘴氣每秒傳遞劑量 +0.05／點（0.5 → 2.0，催毒中 1.0 → 3.5，可調） | 引擎效果（披風）；劑數併入：待決（見 10.4） | `ESSB_P_poison_0_2_M1..M15` 0x004645–0x004653 | 基礎擴散間隔 -0.1 秒／點（2 → 0.5 秒） | **CHANGED** | 擴散間隔 → 瘴氣每秒傳遞劑量；負責「待決」（10.4）；現行：ESSBElem3.SpreadInterval / SpreadTargets → ESSBStatus.Tick；Papyrus 直讀：ESSBElem3×2 |
|  |  | 分支 1 | **侵蝕**：目標中毒滿劑（10）時毒抗 -20% | DLL N3 | `ESSB_P_poison_0_2_B1` 0x0021AC | 侵蝕：毒層 ≥10 時目標毒抗 -20% | **RETUNED** | 毒層 → 劑；現行：ESSBElem3.OnPoisonHit；Papyrus 直讀：ESSBElem3×2 |
|  |  | 分支 2 | **傳染門檻**：擴散門檻 5 劑 → 1 劑 | DLL N3 | `ESSB_P_poison_0_2_B2` 0x0021AD | 傳染門檻：基礎擴散門檻 5 層 → 1 層 | **RETUNED** | 毒層 → 劑；現行：ESSBElem3.SpreadThreshold；Papyrus 直讀：ESSBElem3×1 |
|  | 大師 | 主線 | 同調每段毒附傷 +1%／點 | DLL N2 | `ESSB_P_poison_0_3_M1..M15` 0x004654–0x004662 | 同調每段毒附傷 +1%／點 | **SAME** | 現行：ESSBElem3.PoisonHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcMaster[elem]** |
|  |  | 分支 1 | **蔓延**：死亡擴散的份額 50% → 75% | DLL N5 | `ESSB_P_poison_0_3_B1` 0x0021B0 | 蔓延：中毒目標死亡時毒層傳給附近敵人 | **CHANGED** | 死亡擴散改成基礎機制；分支改為份額 50→75%；現行：ESSBElem3.OnKill；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 2 | **以毒攻毒**：你中毒時生命回復 +20% | 引擎效果 | `ESSB_P_poison_0_3_B2` 0x0021B1 | 以毒攻毒：你中毒時生命回復 +20% | **SAME** | 現行：ESSBElem3.PoisonFormTick → ESSBController.IsPoisoned；Papyrus 直讀：ESSBElem3×1 |
|  | 傳奇 | 主線 | 瘟疫，同調三段時中毒目標每秒自動擴散 1 劑到附近敵人，機率 5%／點 | 待決 | `ESSB_P_poison_0_4_M1..M15` 0x004663–0x004671 | 瘟疫：同調三段時毒層每秒自動擴散到附近敵人，機率 5%／點 | **RETUNED** | 毒層 → 1 劑；負責「待決」；現行：ESSBElem3.PoisonTickHook ← ESSBStatus.Tick；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 1 | **百毒不侵**：同調三段時免疫中毒與疾病，附近中毒敵人每秒替你回血 | 引擎效果（免疫）＋Papyrus（每秒掃描回血） | `ESSB_P_poison_0_4_B1` 0x0021B4 | 百毒不侵：同調三段時免疫中毒與疾病，附近中毒敵人每秒替你回血 | **SAME** | 現行：ESSBElem3.PoisonFormTick；Papyrus 直讀：ESSBElem3×1 |
| 開啟（毒臨） | 新手 | 主線 | 開印劑數 +1／每 3 點（3 → 8） | DLL N3 | `ESSB_P_poison_1_0_M1..M15` 0x004672–0x004680 | 開印毒層 +1／每 3 點 | **RETUNED** | 毒層 → 劑數（3 → 8）；現行：ESSBElem3.OpenStacks → ESSBReactions.Open；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 1 | **毒濺**：開印時附近 1 人中毒 2 劑 | DLL N3（掃描 N5） | `ESSB_P_poison_1_0_B1` 0x0021B8 | 毒濺：開印時附近 1 人 +2 毒層 | **RETUNED** | 毒層 → 劑；現行：ESSBElem3.OpenPoison；Papyrus 直讀：ESSBElem3×1 |
|  | 熟練 | 主線 | 開印後 5 秒內毒附傷 +1%／點 | DLL N3 | `ESSB_P_poison_1_1_M1..M15` 0x004681–0x00468F | 開印後 5 秒內毒附傷 +1%／點 | **SAME** | 現行：ESSBElem3.PoisonHitMult（GetOpenBoost）；Papyrus 直讀：ESSBElem3×1；Papyrus 共用：ESSBController.DifferencePossible／開印加成 |
|  |  | 分支 1 | **濃毒**：開印時若 6 公尺內已有中毒的敵人，從劑數最高的那一個複製 2 劑到新目標（不從對方扣） | DLL N3（掃描 N5） | `ESSB_P_poison_1_1_B1` 0x0021BC | 濃毒：開印那一擊附傷 ×1.5 | **CHANGED** | 開印 ×1.5 → 從附近中毒者複製 2 劑；現行：ESSBElem.OpenStrikeMult；Papyrus 共用：ESSBElem.OpenStrikeMult ×1.5＋ESSBController.DifferencePossible（各元素共用） |
|  |  | 分支 2 | **毒膜**：開印時毒抗 +50% 5 秒 | DLL N3 | `ESSB_P_poison_1_1_B2` 0x0021BD | 毒膜：開印時毒抗 +50% 5 秒 | **SAME** | 現行：ESSBElem3.OpenPoison；Papyrus 直讀：ESSBElem3×1 |
|  | 專精 | 主線 | 毒印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_poison_1_2_M1..M15` 0x004690–0x00469E | 毒印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBElem.MarkDurationBonus；Papyrus 共用：ESSBElem.MarkDurationBonus |
|  |  | 分支 1 | **毒臨強化**：毒臨時範圍內敵人中毒 3 劑 | Papyrus＋DLL N5 | `ESSB_P_poison_1_2_B1` 0x0021C0 | 毒臨強化：毒臨時範圍內敵人 +3 毒層 | **RETUNED** | 毒層 → 劑；現行：ESSBElem3.OnFormOpened(8)；Papyrus 直讀：ESSBElem3×1 |
|  | 大師 | 主線 | 毒臨，開毒形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | Papyrus＋DLL N5 | `ESSB_P_poison_1_3_M1..M15` 0x00469F–0x0046AD | 毒臨：開毒形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem.OnFormOpened；Papyrus 共用：ESSBElem.OnFormOpened（X 臨） |
|  |  | 分支 1 | **腐蝕開印**：開印目標毒抗 -10% | DLL N3 | `ESSB_P_poison_1_3_B1` 0x0021C4 | 腐蝕開印：開印目標毒抗 -10% | **SAME** | 現行：ESSBElem3.OpenPoison；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 2 | **毒血**：開印時你回血 B_max ×0.5 | DLL N3 | `ESSB_P_poison_1_3_B2` 0x0021C5 | 毒血：開印時你回血 B_max ×0.5 | **SAME** | 現行：ESSBElem3.OpenPoison；Papyrus 直讀：ESSBElem3×1 |
|  | 傳奇 | 主線 | 開印效果 +3%／點 | DLL N3 | `ESSB_P_poison_1_4_M1..M15` 0x0046AE–0x0046BC | 開印效果 +3%／點 | **SAME** | 現行：ESSBElem.OpenMult；Papyrus 共用：ESSBElem.OpenMult |
|  |  | 分支 1 | **劇毒之始**：同調三段時開印劑數 ×2 | DLL N3 | `ESSB_P_poison_1_4_B1` 0x0021C8 | 劇毒之始：同調三段時開印毒層 ×2 | **RETUNED** | 毒層 → 劑數；現行：ESSBElem3.OpenPoison；Papyrus 直讀：ESSBElem3×1 |
| 關閉（催毒） | 新手 | 主線 | 終焉 +2%／點 | DLL N3（融斷 N5） | `ESSB_P_poison_2_0_M1..M15` 0x0046BD–0x0046CB | 終焉 +2%／點 | **SAME** | 現行：ESSBElem.EndMult；Papyrus 共用：ESSBElem.EndMult |
|  |  | 分支 1 | **潰爛**：催毒改為強度 ×3 | DLL N3 | `ESSB_P_poison_2_0_B1` 0x0021CC | 潰爛：催毒期間改為每秒跳三次 | **RETUNED** | 每秒跳三次 → 強度 ×3（同倍率，實作改寫強度）；現行：ESSBElem3.CatalyzeRate → ESSBStatus.Tick；Papyrus 直讀：ESSBElem3×1 |
|  | 熟練 | 主線 | 毒印記的融斷 +2%／點 | DLL N5 | `ESSB_P_poison_2_1_M1..M15` 0x0046CC–0x0046DA | 毒印記的融斷 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **延毒**：催毒時剩餘時長 +4 秒 | DLL N3 | `ESSB_P_poison_2_1_B1` 0x0021D0 | 延毒：催毒 8 → 12 秒 | **RETUNED** | 催毒 8→12 秒 → 剩餘時長 +4 秒；現行：ESSBElem3.CatalyzeSeconds；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 2 | **疫染**：毒終焉時把目標的中毒（同強度同剩餘）複製到 6 公尺內敵人 | DLL N5 | `ESSB_P_poison_2_1_B2` 0x0021D1 | 瘴氣：毒終焉時毒層以原層數複製到 6 公尺內敵人 | **RETUNED** | 改名（「瘴氣」改指基礎披風）；毒層複製 → 中毒同強度同剩餘複製；現行：ESSBElem3.EndPoisonNodes；Papyrus 直讀：ESSBElem3×1 |
|  | 專精 | 主線 | 終焉後 5 秒內接管元素附傷 +1%／點 | DLL N3 | `ESSB_P_poison_2_2_M1..M15` 0x0046DB–0x0046E9 | 終焉後 5 秒內接管元素附傷 +1%／點 | **SAME** | 現行：ESSBElem.OnEnd → ESSBController.SetEndBoost / GetHitMult；Papyrus 共用：ESSBElem（SetEndBoost，任何樹這格有點數都會觸發） |
|  |  | 分支 1 | **毒斷**：融斷的催毒改為強度 ×4 | DLL N5 | `ESSB_P_poison_2_2_B1` 0x0021D4 | 毒斷：融斷的催毒持續 ×2 | **CHANGED** | 催毒持續 ×2 → 強度 ×4；現行：ESSBElem3.CatalyzeSeconds（aiReason == 1）；Papyrus 直讀：ESSBElem3×1 |
|  | 大師 | 主線 | 毒印記的融斷再 +2%／點 | DLL N5 | `ESSB_P_poison_2_3_M1..M15` 0x0046EA–0x0046F8 | 毒印記的融斷再 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **劇毒**：催毒期間目標毒抗視為 0 | DLL N3 | `ESSB_P_poison_2_3_B1` 0x0021D8 | 劇毒：催毒期間目標毒抗視為 0 | **SAME** | 現行：ESSBElem3.ApplyVirulence；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 2 | **腐蝕終焉**：毒終焉後目標魔抗 -20% 8 秒 | DLL N3 | `ESSB_P_poison_2_3_B2` 0x0021D9 | 腐蝕終焉：毒終焉後目標魔抗 -20% 8 秒 | **SAME** | 現行：ESSBElem3.EndPoisonNodes；Papyrus 直讀：ESSBElem3×1 |
|  | 傳奇 | 主線 | 催毒期間中毒傷害 +3%／點 | DLL N3（融斷 N5） | `ESSB_P_poison_2_4_M1..M15` 0x0046F9–0x004707 | 催毒期間毒層傷害 +3%／點 | **RETUNED** | 毒層傷害 → 中毒傷害；現行：ESSBElem3.PoisonTickMult（催毒中）；Papyrus 直讀：ESSBElem3×1；Papyrus 共用：ESSBElem.SignatureMult |
|  |  | 分支 1 | **毒霧**：毒印記融斷後留下 5 秒毒霧，內部敵人每秒中毒 +1 劑 | Papyrus（領域）；劑數併入：待決 | `ESSB_P_poison_2_4_B1` 0x0021DC | 毒霧：毒印記融斷後留下 5 秒毒霧，內部每秒 +1 毒層 | **RETUNED** | 毒層 → 劑；劑數併入「待決」；現行：ESSBElem3.EndPoisonNodes → ESSBController.StartDomain(8, 5)；Papyrus 直讀：ESSBElem3×1 |

### 5.11 水（`water`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續（潮汐） | 新手 | 主線 | 浸濕持續 +0.3 秒／點（只延長浸濕本身，不影響水印記時長） | DLL N3 | `ESSB_P_water_0_0_M1..M15` 0x004708–0x004716 | 浸濕持續 +0.3 秒／點 | **SAME** | v0.4 只補充說明；現行：ESSBElem3.WetSeconds → ESSBStatus.Tick；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 1 | **清流**：命中回復耐力 30 | DLL N2 | `ESSB_P_water_0_0_B1` 0x0021E0 | 清流：命中回復耐力 5 | **SAME** | v0.3 文字 5，但 settings.json water_clear_stamina 已是 30，遊戲內已是 v0.4 數字；現行：ESSBElem3.OnWaterHit；**DLL：kWaterClearStream** |
|  | 熟練 | 主線 | 長流每秒回復 +0.2%／點（2.0% → 5.0%；只加生命與耐力） | Papyrus | `ESSB_P_water_0_1_M1..M15` 0x004717–0x004725 | 長流每秒回復 +0.02%／點（0.3% → 0.6%） | **RETUNED** | v0.3 文字 0.3→0.6%，settings 已覆寫為 2.0→5.0%；v0.4 另限「只加生命與耐力」；現行：ESSBElem3.FlowPercent → WaterFormTick；Papyrus 直讀：ESSBElem3×1；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像） |
|  |  | 分支 1 | **水壓**：命中浸濕目標 +1 水壓，每層水附傷 +10% | DLL N3 | `ESSB_P_water_0_1_B1` 0x0021E4 | 水壓：命中浸濕目標 +1 水壓，每層水附傷 +10% | **SAME** | 現行：ESSBElem3.OnWaterHit + WaterHitMult；Papyrus 直讀：ESSBController×1、ESSBElem3×2 |
|  |  | 分支 2 | **水盾**：水幕的分擔比例 20% → 30%，效率每擋 1 點傷害 1.5 → 1.0 點魔力 | 引擎效果（PERK）＋DLL 受擊 N4 | （無） | — | **NEW** | 水幕分擔 20→30%、效率 1.5→1.0（PERK＋DLL 受擊）；— |
|  |  | （移除） | — | — | `ESSB_P_water_0_1_B2` 0x0021E5 | 水膜：浸濕目標對你的傷害 -10% | **REMOVED** | 浸濕攻擊者傷害 -10%（PERK 0x24 分頁 1）；現行：PERK ESSB_P_water_0_1_B2 進入點 0x24 分頁 1；ESP 進入點：0x24 分頁1 |
|  | 專精 | 主線 | 水壓每層水附傷 +1%／點 | DLL N3 | `ESSB_P_water_0_2_M1..M15` 0x004726–0x004734 | 水壓每層水附傷 +1%／點 | **SAME** | 現行：ESSBElem3.WaterHitMult；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 1 | **洗淨**：命中時清除自身一個負面效果（中毒、疾病、元素持續傷、減速），每 3 秒一次 | DLL N4 | `ESSB_P_water_0_2_B1` 0x0021E8 | 洗淨：命中時清除自身一個負面效果（中毒、疾病、元素持續傷、減速），每 3 秒一次 | **SAME** | 現行：ESSBElem3.OnWaterHit → ESSBController.TakeCleanse / ApplyCle…；Papyrus 直讀：ESSBElem3×1 |
|  | 大師 | 主線 | 同調每段長流回復 +0.05%／點 | Papyrus | `ESSB_P_water_0_3_M1..M15` 0x004735–0x004743 | 同調每段長流回復 +0.05%／點 | **SAME** | 現行：ESSBElem3.FlowPercent；Papyrus 直讀：ESSBElem3×1；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像） |
|  |  | 分支 1 | **潮身**：水幕把魔力扣到 0 的那一刻，立即洗淨一次（不佔洗淨冷卻）並回復最大魔力 20%，水幕馬上恢復，每 30 秒一次 | DLL 受擊 N4 | （無） | — | **NEW** | 水幕扣到 0 時洗淨＋回 20% 魔力；— |
|  |  | 分支 2 | **淨化**：洗淨改為清除全部負面效果 | DLL N4 | `ESSB_P_water_0_3_B2` 0x0021ED | 淨化：洗淨改為清除全部負面效果 | **SAME** | 現行：ESSBController.ApplyCleanse(True) → DispelHostileEffects（SPE…；Papyrus 直讀：ESSBElem3×1 |
|  |  | （移除） | — | — | `ESSB_P_water_0_3_B1` 0x0021EC | 水鏡：每命中 +1 層（最多 3），被打消耗一層抵消該次 30% 傷害 | **REMOVED** | 被打抵消 30%（PERK 0x24；ESSBController.RefreshRecovery 用 SetNthEntryValue 改這格）；現行：ESSBElem3.OnWaterHit + ESSBGuard.OnHitEx + PERK ESSB_P_water…；Papyrus 直讀：ESSBController(GetBranch+SetNthEntryValue)×1、ESSBElem3×1；ESP 進入點：0x24 |
|  | 傳奇 | 主線 | 長河，同調三段時長流再 +0.05%／點，且長流同時作用於附近同伴 | Papyrus | `ESSB_P_water_0_4_M1..M15` 0x004744–0x004752 | 長河：同調三段時長流再 +0.05%／點，且長流同時作用於附近同伴 | **SAME** | 現行：ESSBElem3.FlowPercent / WaterFormTick；Papyrus 直讀：ESSBElem3×2 |
|  |  | 分支 1 | **止水**：同調三段時水幕分擔比例再 +15%（配水盾為 45%） | 引擎效果（PERK） | （無） | — | **NEW** | 同調三段水幕再 +15%（PERK）；— |
|  |  | （移除） | — | — | `ESSB_P_water_0_4_B1` 0x0021F0 | 水體：同調三段時受傷 -15%，火傷減半 | **REMOVED** | 同調三段受傷 -15%、火傷減半（PERK 0x24＋0x29）；現行：PERK ESSB_P_water_0_4_B1 進入點 0x24 與 0x29；ESP 進入點：0x24＋0x29 |
| 開啟（水臨） | 新手 | 主線 | 開印時回復生命與耐力各最大值 0.3%／點（15 點 4.5%） | DLL N3 | `ESSB_P_water_1_0_M1..M15` 0x004753–0x004761 | 浸濕減速 +1%／點 | **CHANGED** | 浸濕減速 +1%／點 → 開印回復生命耐力 0.3%／點（native kWaterSoakSlow 讀這一格）；現行：ESSBElem3.WetSlow → ESSBReactions.Open；Papyrus 直讀：ESSBElem3×1；**DLL：kWaterSoakSlow** |
|  |  | 分支 1 | **廣佈**：開印時浸濕擴散到附近 1 人 | DLL N3（掃描 N5） | `ESSB_P_water_1_0_B1` 0x0021F4 | 廣佈：開印時浸濕擴散到附近 1 人 | **SAME** | 現行：ESSBElem3.OpenWater；Papyrus 直讀：ESSBElem3×1 |
|  | 熟練 | 主線 | 開印後 5 秒內水附傷 +1%／點 | DLL N3 | `ESSB_P_water_1_1_M1..M15` 0x004762–0x004770 | 開印後 5 秒內水附傷 +1%／點 | **SAME** | 現行：ESSBElem3.WaterHitMult（GetOpenBoost）；Papyrus 直讀：ESSBElem3×1；Papyrus 共用：ESSBController.DifferencePossible／開印加成 |
|  |  | 分支 1 | **深濕**：開印時若下雨、下雪或你站在水中，目標水壓直接滿格（立即沖刷；需已取得水壓） | DLL N3 | `ESSB_P_water_1_1_B1` 0x0021F8 | 深濕：開印那一擊附傷 ×1.5 | **CHANGED** | 開印 ×1.5 → 天候／站水中水壓直接滿；現行：ESSBElem.OpenStrikeMult；Papyrus 共用：ESSBElem.OpenStrikeMult ×1.5＋ESSBController.DifferencePossible（各元素共用） |
|  |  | 分支 2 | **湧泉**：開印時回復耐力 80 | DLL N3 | `ESSB_P_water_1_1_B2` 0x0021F9 | 回流：開印時回復耐力 15 | **RETUNED** | 改名；v0.3 文字 15，settings water_open_stamina 已是 80；現行：ESSBElem3.OpenWater；Papyrus 直讀：ESSBElem3×1 |
|  | 專精 | 主線 | 水印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_water_1_2_M1..M15` 0x004771–0x00477F | 水印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBElem.MarkDurationBonus；Papyrus 共用：ESSBElem.MarkDurationBonus |
|  |  | 分支 1 | **水臨強化**：水臨時範圍內敵人浸濕，你立即清除全部負面效果並回滿魔力（開場就是滿的水幕） | Papyrus＋DLL N5 | `ESSB_P_water_1_2_B1` 0x0021FC | 水臨強化：水臨時範圍內敵人浸濕並減速 20%，你立即清除全部負面效果 | **CHANGED** | 拿掉減速 20%，改為回滿魔力；現行：ESSBElem3.OnFormOpened(9)；Papyrus 直讀：ESSBElem3×1 |
|  | 大師 | 主線 | 水臨，開水形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | Papyrus＋DLL N5 | `ESSB_P_water_1_3_M1..M15` 0x004780–0x00478E | 水臨：開水形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem.OnFormOpened；Papyrus 共用：ESSBElem.OnFormOpened（X 臨） |
|  |  | 分支 1 | **開印沖刷**：開印額外驅散目標一個有時限的增益，每目標每 10 秒一次（獨立於水壓滿格的沖刷） | DLL N3 | `ESSB_P_water_1_3_B1` 0x002200 | 沖刷：開印驅散目標一個有時限的增益（護甲術、披風、隱身等法術），每目標每 10 秒一次 | **RETUNED** | 改名，效果相同；現行：ESSBElem3.OpenWater → ESSBController.ApplyStrip（SPEL ESSB_St…；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 2 | **淨潮**：任何沖刷（水壓滿格、開印沖刷、退潮、洗滌）每清掉目標一個增益，你回復生命與魔力各 B_max ×2 | DLL N3 | （無） | — | **NEW** | 每沖刷一個增益回血回魔；— |
|  |  | （移除） | — | — | `ESSB_P_water_1_3_B2` 0x002201 | 水牢：浸濕目標移速 -20% | **REMOVED** | 浸濕移速 -20%（減速只在冰）；現行：ESSBElem3.OnWaterHit；Papyrus 直讀：ESSBElem3×1 |
|  | 傳奇 | 主線 | 開印效果 +3%／點 | DLL N3 | `ESSB_P_water_1_4_M1..M15` 0x00478F–0x00479D | 開印效果 +3%／點 | **SAME** | 現行：ESSBElem.OpenMult；Papyrus 共用：ESSBElem.OpenMult |
|  |  | 分支 1 | **汪洋之始**：同調三段時開印的浸濕不會過期，直到被切掉 | DLL N3 | `ESSB_P_water_1_4_B1` 0x002204 | 汪洋之始：同調三段時開印的浸濕不會過期，直到被切掉 | **SAME** | 現行：ESSBElem3.OpenWater → ESSBController.SetWetLock → ESSBStatus；Papyrus 直讀：ESSBElem3×1 |
| 關閉（導引） | 新手 | 主線 | 終焉 +2%／點 | DLL N3（融斷 N5） | `ESSB_P_water_2_0_M1..M15` 0x00479E–0x0047AC | 終焉 +2%／點 | **SAME** | 現行：ESSBElem.EndMult；Papyrus 共用：ESSBElem.EndMult |
|  |  | 分支 1 | **強引**：導引 ×1.5 → ×2.0 | DLL N3 | `ESSB_P_water_2_0_B1` 0x002208 | 強引：導引 ×1.5 → ×2.0 | **SAME** | 現行：ESSBElem3.GuideMult；Papyrus 直讀：ESSBElem3×1 |
|  | 熟練 | 主線 | 水印記的融斷 +2%／點 | DLL N5 | `ESSB_P_water_2_1_M1..M15` 0x0047AD–0x0047BB | 水印記的融斷 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **退潮**：水印記被切或融斷時，對目標沖刷一次（不需水壓滿格，每目標 10 秒一次） | DLL N3（融斷 N5） | （無） | — | **NEW** | 被切／融斷時沖刷一次；— |
|  |  | 分支 2 | **水斷**：水印記融斷改為治療你並回復耐力 | DLL N5 | `ESSB_P_water_2_1_B2` 0x00220D | 水斷：水印記融斷改為治療你並回復耐力 | **SAME** | 現行：ESSBElem3.EndWaterNodes；Papyrus 直讀：ESSBElem3×1 |
|  |  | （移除） | — | — | `ESSB_P_water_2_1_B1` 0x00220C | 潮引：水終焉時接管元素 +5 → +10 同調 | **REMOVED** | 接管元素 +5→+10 同調；現行：ESSBElem3.GuideSync → ESSBReactions.EndWater；Papyrus 直讀：ESSBElem3×1 |
|  | 專精 | 主線 | 終焉後 5 秒內接管元素附傷 +1%／點 | DLL N3 | `ESSB_P_water_2_2_M1..M15` 0x0047BC–0x0047CA | 終焉後 5 秒內接管元素附傷 +1%／點 | **SAME** | 現行：ESSBElem.OnEnd → ESSBController.SetEndBoost；Papyrus 共用：ESSBElem（SetEndBoost，任何樹這格有點數都會觸發） |
|  |  | 分支 1 | **汪洋**：水終焉時目標的浸濕延長到 30 秒（不需要水印記；水壓、爆燃、大潮照常讀它） | DLL N3 | `ESSB_P_water_2_2_B1` 0x002210 | 汪洋：水終焉不移除浸濕，保留為副印記 10 秒，融斷時再結算 | **CHANGED** | 副印記 10 秒 → 浸濕延長到 30 秒；現行：ESSBElem3.EndWaterNodes → ESSBController.KeepAsSecond；Papyrus 直讀：ESSBController×1、ESSBElem3×1 |
|  | 大師 | 主線 | 水印記的融斷再 +2%／點 | DLL N5 | `ESSB_P_water_2_3_M1..M15` 0x0047CB–0x0047D9 | 水印記的融斷再 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **大潮**：水終焉時範圍內所有浸濕目標都給接管元素導引 | DLL N5 | `ESSB_P_water_2_3_B1` 0x002214 | 大潮：水終焉時範圍內所有浸濕目標都給接管元素導引 | **SAME** | 現行：ESSBElem3.EndWaterNodes → ESSBController.SetNextEndMultOn；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 2 | **洗滌**：水終焉清除你所有負面效果，並驅散目標一個有時限的增益 | DLL N3 | `ESSB_P_water_2_3_B2` 0x002215 | 洗滌：水終焉清除你所有負面效果，並驅散目標一個有時限的增益 | **SAME** | 現行：ESSBElem3.EndWaterNodes；Papyrus 直讀：ESSBElem3×1 |
|  | 傳奇 | 主線 | 導引 +3%／點 | DLL N3 | `ESSB_P_water_2_4_M1..M15` 0x0047DA–0x0047E8 | 導引 +3%／點 | **SAME** | 現行：ESSBElem3.GuideMult（ESSBElem.SignatureMult）；Papyrus 共用：ESSBElem.SignatureMult |
|  |  | 分支 1 | **潮池**：水印記融斷後留下 5 秒水域，你在其中回血回耐力並每秒洗淨一次；內部敵人每秒被沖刷一個增益 | Papyrus（領域；沖刷呼叫 DLL 原生函式） | `ESSB_P_water_2_4_B1` 0x002218 | 潮池：水印記融斷後留下 5 秒水域，內部敵人減速 30%、你回血回耐力 | **CHANGED** | 拿掉減速 30%，加上每秒洗淨與沖刷；現行：ESSBElem3.EndWaterNodes → ESSBController.StartDomain(9, 5)；Papyrus 直讀：ESSBElem3×1 |

### 5.12 黑暗（`darkness`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續（侵蝕） | 新手 | 主線 | 詛咒每層抗性侵蝕 -0.2%／點（-2% → -5%） | DLL N3 | `ESSB_P_darkness_0_0_M1..M15` 0x0047E9–0x0047F7 | 詛咒每層抗性侵蝕 -0.2%／點（-2% → -5%） | **SAME** | 現行：ESSBElem3.ApplyCurseErosion；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 1 | **咒延**：詛咒 ≥3 層的目標，黑暗印記過期時續 4 秒（每目標一次），讓它死時還帶著印記 | DLL N3 | （無） | — | **NEW** | 詛咒 ≥3 時暗印記過期續 4 秒；— |
|  |  | （移除） | — | — | `ESSB_P_darkness_0_0_B1` 0x00221C | 蝕魔：命中吸魔 ×2 | **REMOVED** | 命中吸魔 ×2；現行：ESSBElem3.OnDarkHit；Papyrus 直讀：ESSBElem3×1 |
|  | 熟練 | 主線 | 暗附傷 +1%／點 | DLL N2 | `ESSB_P_darkness_0_1_M1..M15` 0x0047F8–0x004806 | 暗附傷 +1%／點 | **SAME** | 現行：ESSBElem3.DarkHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcAdept[elem]** |
|  |  | 分支 1 | **懼咒**：恐懼門檻 3 → 2 層 | DLL N3 | （無） | — | **NEW** | 恐懼門檻 3 → 2；— |
|  |  | 分支 2 | **怨縛**：詛咒目標打你時，它的詛咒 +1（每目標 2 秒一次） | DLL 受擊 N4 | （無） | — | **NEW** | 詛咒目標打你時詛咒 +1；— |
|  |  | （移除） | — | — | `ESSB_P_darkness_0_1_B1` 0x002220 | 衰弱：詛咒目標攻擊 -10% | **REMOVED** | 詛咒目標攻擊 -10%；現行：ESSBElem3.OnDarkHit；Papyrus 直讀：ESSBElem3×1 |
|  |  | （移除） | — | — | `ESSB_P_darkness_0_1_B2` 0x002221 | 影甲：詛咒目標對你的傷害 -10% | **REMOVED** | 詛咒目標對你傷害 -10%（PERK 0x24 分頁 1）；現行：PERK ESSB_P_darkness_0_1_B2 進入點 0x24 分頁 1；ESP 進入點：0x24 分頁1 |
|  | 專精 | 主線 | 幻覺持續 +0.1 秒／點（恐懼 2 → 3.5 秒、瘋狂 3 → 4.5 秒） | DLL N3 | `ESSB_P_darkness_0_2_M1..M15` 0x004807–0x004815 | 詛咒滿層目標受所有傷害 +1%／點 | **CHANGED** | 滿層受所有傷害 +1% → 幻覺持續 +0.1 秒；現行：ESSBElem3.TargetDamageMult → ESSBController.ApplyDamage / Ge…；Papyrus 直讀：ESSBController×1、ESSBElem3×1 |
|  |  | 分支 1 | **狂咒**：瘋狂門檻 5 → 4 層 | DLL N3 | （無） | — | **NEW** | 瘋狂門檻 5 → 4；— |
|  |  | （移除） | — | — | `ESSB_P_darkness_0_2_B1` 0x002224 | 腐朽：詛咒目標受治療 -50% | **REMOVED** | 受治療 -50%；現行：ESSBElem3.OnDarkHit（ESSB_Util_HealRateDebuff）；Papyrus 直讀：ESSBElem3×1 |
|  | 大師 | 主線 | 同調每段暗附傷 +1%／點 | DLL N2 | `ESSB_P_darkness_0_3_M1..M15` 0x004816–0x004824 | 同調每段暗附傷 +1%／點 | **SAME** | 現行：ESSBElem3.DarkHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcMaster[elem]** |
|  |  | 分支 1 | **狂宴**：瘋狂中的敵人殺死的目標，視為帶黑暗印記死亡（詛咒門檻照常） | DLL N5（兇手判定見 10.3） | （無） | — | **NEW** | 瘋狂者殺的目標視為帶暗印記死亡（兇手判定見 10.3）；— |
|  |  | 分支 2 | **回魘**：恐懼或瘋狂結束時，目標詛咒 +2 層（幻覺醒來，詛咒更深） | DLL N3 | （無） | — | **NEW** | 幻覺結束詛咒 +2；— |
|  |  | （移除） | — | — | `ESSB_P_darkness_0_3_B1` 0x002228 | 虛空：對魔力低於 25% 的施法者傷害 ×1.5 | **REMOVED** | 對低魔施法者 ×1.5；現行：ESSBElem3.DarkHitMult → ESSBNoForm.IsSpellUser；Papyrus 直讀：ESSBController×1、ESSBElem3×1 |
|  |  | （移除） | — | — | `ESSB_P_darkness_0_3_B2` 0x002229 | 收割：詛咒目標死亡回魔 | **REMOVED** | 詛咒目標死亡回魔；現行：ESSBElem3.OnKill；Papyrus 直讀：ESSBElem3×1 |
|  | 傳奇 | 主線 | 深淵，同調三段時詛咒層上限 +1／每 3 點，滿層目標抗性可侵蝕到負值 | DLL N3 | `ESSB_P_darkness_0_4_M1..M15` 0x004825–0x004833 | 深淵：同調三段時詛咒層上限 +1／每 3 點，滿層目標抗性可侵蝕到負值 | **SAME** | 現行：ESSBElem3.CurseCap → ESSBController.StackCap；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 1 | **亡衛**：同調三段時，你復生的僕從死亡時爆出 3 公尺 B_max ×1.0 暗傷，範圍內敵人詛咒 +2 層 | DLL N5 | （無） | — | **NEW** | 僕從死亡爆暗傷；— |
|  |  | （移除） | — | — | `ESSB_P_darkness_0_4_B1` 0x00222C | 影身：同調三段時被近戰命中 30% 機率無效並回魔 | **REMOVED** | 30% 無效並回魔（PERK 0x24，讀 GuardDark）；現行：ESSBGuard.OnHitEx → ESSBElem3.OnShadowBody + PERK ESSB_P_dar…；Papyrus 直讀：ESSBElem3×1；ESP 進入點：0x24 |
| 開啟（咒縛） | 新手 | 主線 | 開印詛咒 +1 層／每 5 點 | DLL N3 | `ESSB_P_darkness_1_0_M1..M15` 0x004834–0x004842 | 開印詛咒 +1 層／每 5 點 | **SAME** | 現行：ESSBElem3.OpenStacks → ESSBReactions.Open；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 1 | **夢魘**：目標恐懼時，3 公尺內其他敵人詛咒 +1（每次恐懼一次） | DLL N3（掃描 N5） | `ESSB_P_darkness_1_0_B1` 0x002230 | 夢魘：開印施加恐懼 1.5 秒 | **CHANGED** | 開印恐懼 1.5 秒 → 恐懼時附近詛咒 +1（恐懼改成基礎幻覺階梯）；現行：ESSBElem3.OpenDark → ESSBController.ApplyFear（MGEF ESSB_Fear…；Papyrus 直讀：ESSBElem3×1 |
|  | 熟練 | 主線 | 開印後 5 秒內暗附傷 +1%／點 | DLL N3 | `ESSB_P_darkness_1_1_M1..M15` 0x004843–0x004851 | 開印後 5 秒內暗附傷 +1%／點 | **SAME** | 現行：ESSBElem3.DarkHitMult（GetOpenBoost）；Papyrus 直讀：ESSBElem3×1；Papyrus 共用：ESSBController.DifferencePossible／開印加成 |
|  |  | 分支 1 | **狂刃**：瘋狂中的目標造成的傷害 +50%（砍它的同伴更痛） | 引擎效果（掛在瘋狂 MGEF 上） | （無） | — | **NEW** | 瘋狂中目標傷害 +50%（掛在瘋狂 MGEF）；— |
|  |  | 分支 2 | **幻影**：開印後 3 秒目標對你的命中率 -30% | DLL N3 | `ESSB_P_darkness_1_1_B2` 0x002235 | 幻影：開印後 3 秒目標對你的命中率 -30% | **SAME** | 現行：ESSBElem3.OpenDark；Papyrus 直讀：ESSBElem3×1 |
|  |  | （移除） | — | — | `ESSB_P_darkness_1_1_B1` 0x002234 | 瘋狂：開印使目標 3 秒內攻擊最近的任何人 | **REMOVED** | 改成基礎幻覺階梯（詛咒 5 層）；現行：ESSBElem3.OpenDark → ESSBController.ApplyFrenzy（MGEF ESSB_Fr…；Papyrus 直讀：ESSBElem3×1；Papyrus 共用：ESSBElem.OpenStrikeMult ×1.5＋ESSBController.DifferencePossible（各元素共用） |
|  | 專精 | 主線 | 暗印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_darkness_1_2_M1..M15` 0x004852–0x004860 | 暗印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBElem.MarkDurationBonus；Papyrus 共用：ESSBElem.MarkDurationBonus |
|  |  | 分支 1 | **暗臨強化**：暗臨時範圍內敵人恐懼 2 秒 | Papyrus＋DLL N5 | `ESSB_P_darkness_1_2_B1` 0x002238 | 暗臨強化：暗臨時範圍內敵人恐懼 2 秒 | **SAME** | 現行：ESSBElem3.OnFormOpened(10)；Papyrus 直讀：ESSBElem3×1 |
|  | 大師 | 主線 | 暗臨，開暗形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | Papyrus＋DLL N5 | `ESSB_P_darkness_1_3_M1..M15` 0x004861–0x00486F | 暗臨：開暗形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | **SAME** | 現行：ESSBElem.OnFormOpened；Papyrus 共用：ESSBElem.OnFormOpened（X 臨） |
|  |  | 分支 1 | **迷亂**：瘋狂中的目標被你命中時詛咒 +2 層 | DLL N3 | `ESSB_P_darkness_1_3_B1` 0x00223C | 迷亂：開印目標 3 秒內無法施法（同沉默實作） | **CHANGED** | 開印沉默 3 秒 → 瘋狂中被命中詛咒 +2；現行：ESSBElem3.OpenDark → ESSBController.ApplySilenceSpell；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 2 | **暗染**：開印時附近 1 人也詛咒 | DLL N3（掃描 N5） | `ESSB_P_darkness_1_3_B2` 0x00223D | 暗染：開印時附近 1 人也詛咒 | **SAME** | 現行：ESSBElem3.OpenDark；Papyrus 直讀：ESSBElem3×1 |
|  | 傳奇 | 主線 | 開印效果 +3%／點 | DLL N3 | `ESSB_P_darkness_1_4_M1..M15` 0x004870–0x00487E | 開印效果 +3%／點 | **SAME** | 現行：ESSBElem.OpenMult；Papyrus 共用：ESSBElem.OpenMult |
|  |  | 分支 1 | **群魔**：同調三段時，目標達到瘋狂門檻那一刻，4 公尺內所有詛咒 ≥3 層的敵人一起瘋狂 3 秒（各自冷卻照算） | DLL N3（掃描 N5）＋Papyrus | `ESSB_P_darkness_1_4_B1` 0x002240 | 群魔：同調三段時開印的瘋狂改為範圍，範圍內敵人互相攻擊 3 秒 | **CHANGED** | 開印瘋狂範圍化 → 達瘋狂門檻時 4 公尺詛咒 ≥3 者一起瘋狂；現行：ESSBElem3.OpenDark；Papyrus 直讀：ESSBElem3×1 |
| 關閉（死咒） | 新手 | 主線 | 終焉 +2%／點 | DLL N3（融斷 N5） | `ESSB_P_darkness_2_0_M1..M15` 0x00487F–0x00488D | 終焉 +2%／點 | **SAME** | 現行：ESSBElem.EndMult；Papyrus 共用：ESSBElem.EndMult |
|  |  | 分支 1 | **饕餮**：死咒結算時吸血吸魔各 B_max ×1.0 | DLL N3 | `ESSB_P_darkness_2_0_B1` 0x002244 | 饕餮：死咒結算時吸血吸魔各 B_max ×1.0 | **SAME** | 現行：ESSBElem3.AfterDeathCurse ← ESSBStatus.Tick；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 2 | **殘魂**：帶黑暗印記死亡、但詛咒只有 1～2 層的敵人也有 25% 機率復生（依等級表的階級） | DLL N5＋Papyrus | （無） | — | **NEW** | 詛咒 1～2 層也 25% 復生；— |
|  |  | （移除） | — | — | `ESSB_P_darkness_2_0_B2` 0x002245 | 亡者歸來：因黑暗傷害死亡的敵人 25% 機率立即復生為你的僕從，階級與持續依目標等級（見下），不超過你的召喚上限 | **REMOVED** | 改成基礎死亡機制；現行：ESSBElem3.Reanimate → ESSBController.ApplyReanimate（MGEF ESS…；Papyrus 直讀：ESSBElem3×1 |
|  | 熟練 | 主線 | 暗印記的融斷 +2%／點 | DLL N5 | `ESSB_P_darkness_2_1_M1..M15` 0x00488E–0x00489C | 暗印記的融斷 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **不治**：死咒的無法治療延長到 6 秒 | DLL N3 | `ESSB_P_darkness_2_1_B1` 0x002248 | 不治：死咒的無法治療延長到 6 秒 | **SAME** | 現行：ESSBElem3.DeathCurseSeconds → ESSBReactions.EndDark；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 2 | **冥印**：暗印記被切時，目標留下一顆 8 秒「冥印」，帶冥印死亡視同帶黑暗印記（切到別的元素收尾也能復生） | DLL N3 | （無） | — | **NEW** | 暗印記被切留 8 秒冥印；— |
|  |  | （移除） | — | — | `ESSB_P_darkness_2_1_B2` 0x002249 | 蝕魔終焉：暗終焉後接管元素的下一次終焉附帶吸魔 | **REMOVED** | 下一次終焉附帶吸魔；現行：ESSBElem3.EndDarkNodes → ESSBController.SetPendingDrain → ES…；Papyrus 直讀：ESSBElem3×1 |
|  | 專精 | 主線 | 死咒的「已損失生命」係數 +0.5%／點（15% → 22.5%） | DLL N3 | `ESSB_P_darkness_2_2_M1..M15` 0x00489D–0x0048AB | 死咒的「已損失生命」係數 +0.5%／點（15% → 22.5%） | **SAME** | 現行：ESSBElem3.DeathCurseLostRatio → ESSBStatus.Tick；Papyrus 直讀：ESSBElem3×1；Papyrus 共用：ESSBElem（SetEndBoost，任何樹這格有點數都會觸發） |
|  |  | 分支 1 | **亡魂**：死咒殺死目標時，附近敵人恐懼 2 秒 | DLL N5 | `ESSB_P_darkness_2_2_B1` 0x00224C | 亡魂：死咒殺死目標時，附近敵人恐懼 2 秒 | **SAME** | 現行：ESSBElem3.AfterDeathCurse；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 2 | **噬咒**：死咒結算時消耗目標全部詛咒，每層讓「已損失生命」係數 +3%（吞了就不能拿這些層數換僕從） | DLL N3 | （無） | — | **NEW** | 死咒吞詛咒換係數；— |
|  |  | （移除） | — | — | `ESSB_P_darkness_2_2_B2` 0x00224D | 亡者強化：復生的僕從繼承死前的詛咒層數作為攻擊加成，每層 +10%，持續 ×2 | **REMOVED** | 併入基礎「死時詛咒層數決定僕從」；現行：ESSBElem3.Reanimate（ESSB_Util_MeleeBuff）；Papyrus 直讀：ESSBElem3×1 |
|  | 大師 | 主線 | 暗印記的融斷再 +2%／點 | DLL N5 | `ESSB_P_darkness_2_3_M1..M15` 0x0048AC–0x0048BA | 暗印記的融斷再 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **冥召**：死咒殺死的目標必定復生（無視詛咒門檻與有無印記），僕從階級 +1（最高五階） | DLL N5＋Papyrus | （無） | — | **NEW** | 死咒殺死必定復生；— |
|  |  | 分支 2 | **深淵回響**：暗終焉回滿你的魔力 | DLL N3 | `ESSB_P_darkness_2_3_B2` 0x002251 | 深淵回響：暗終焉回滿你的魔力 | **SAME** | 現行：ESSBElem3.EndDarkNodes；Papyrus 直讀：ESSBElem3×1 |
|  |  | （移除） | — | — | `ESSB_P_darkness_2_3_B1` 0x002250 | 處刑：死咒結算時目標生命低於 15% 則直接死亡，首領與必要角色改為 ×3 | **REMOVED** | 處決只在冰；現行：ESSBElem3.AfterDeathCurse → ESSBController.Execute；Papyrus 直讀：ESSBElem3×1 |
|  | 傳奇 | 主線 | 死咒 +3%／點 | DLL N3 | `ESSB_P_darkness_2_4_M1..M15` 0x0048BB–0x0048C9 | 死咒 +3%／點 | **SAME** | 現行：ESSBElem.SignatureMult → ESSBReactions.EndDark；Papyrus 共用：ESSBElem.SignatureMult |
|  |  | 分支 1 | **死域**：暗印記融斷後留下 5 秒死域，內部敵人無法被治療、每秒受 B_max ×0.5 暗傷 | Papyrus（領域） | `ESSB_P_darkness_2_4_B1` 0x002254 | 死域：暗印記融斷後留下 5 秒死域，內部敵人無法被治療、每秒受 B_max ×0.5 暗傷 | **SAME** | 現行：ESSBElem3.EndDarkNodes → ESSBController.StartDomain(10, 5)；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 2 | **死靈主**：同調三段時亡者歸來不需要詛咒門檻（帶黑暗印記或冥印即可），60 級以上也能復生，且任何等級的僕從可改為永久（六階，永久上限 1 名） | DLL N5＋Papyrus | `ESSB_P_darkness_2_4_B2` 0x002255 | 死靈主：同調三段時亡者歸來機率改為 100%，且任何等級的僕從可改為永久（六階，永久上限 1 名） | **CHANGED** | 復生機率 100% → 不需詛咒門檻、60 級以上可復生；現行：ESSBElem3.Reanimate；Papyrus 直讀：ESSBElem3×1 |

### 5.13 星界（`astral`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續（共鳴） | 新手 | 主線 | 回聲比例 +1%／點（25% → 40%，不吃節點倍率） | DLL N5 | `ESSB_P_astral_0_0_M1..M15` 0x0048CA–0x0048D8 | 星痕延遲傷害 +2%／點 | **CHANGED** | 星痕延遲傷害 → 回聲比例（星改成共鳴機制）；現行：ESSBElem3.AstralTickMult → ESSBStatus.Tick；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 1 | **星鏈**：被回聲打到的共鳴目標星痕 +1 層（不重新計時，每目標每 2 秒一次） | DLL N5 | （無） | — | **NEW** | 回聲讓共鳴目標星痕 +1；— |
|  |  | （移除） | — | — | `ESSB_P_astral_0_0_B1` 0x002258 | 星輝：星形態魔力回復 +20% | **REMOVED** | 星形態魔力回復 +20%；現行：SPEL ESSB_Ability_Induction + ESSBController.RefreshAbilitie…；Papyrus 直讀：ESSBElem3×1 |
|  | 熟練 | 主線 | 星附傷 +1%／點 | DLL N2 | `ESSB_P_astral_0_1_M1..M15` 0x0048D9–0x0048E7 | 星附傷 +1%／點 | **SAME** | 現行：ESSBElem3.AstralHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcAdept[elem]** |
|  |  | 分支 1 | **聚星**：引爆當下若 15 公尺內共鳴目標 ≥3，這次引爆 +30% | DLL N3（計數 N5） | （無） | — | **NEW** | 共鳴 ≥3 時引爆 +30%；— |
|  |  | （移除） | — | — | `ESSB_P_astral_0_1_B1` 0x00225C | 追擊：每第 3 次命中額外 35% 星傷 | **REMOVED** | 每第 3 擊額外 35%；現行：ESSBElem3.OnAstralHit → ESSBController.BumpAstralHits；Papyrus 直讀：ESSBElem3×1 |
|  |  | （移除） | — | — | `ESSB_P_astral_0_1_B2` 0x00225D | 星軌：命中回復魔力 | **REMOVED** | 命中回魔；現行：ESSBElem3.OnAstralHit；Papyrus 直讀：ESSBElem3×1 |
|  | 專精 | 主線 | 星痕層數上限 +1／每 5 點（也提高闇星每一擊） | DLL N3 | `ESSB_P_astral_0_2_M1..M15` 0x0048E8–0x0048F6 | 星痕層數上限 +1／每 5 點 | **SAME** | v0.4 只補充說明；現行：ESSBElem3.AstralCap → ESSBController.StackCap；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 1 | **星痕弱點**：重擊時每層星痕 +8%（闇星一擊以星痕上限計） | DLL N3 | `ESSB_P_astral_0_2_B1` 0x002260 | 星痕弱點：重擊時每層星痕 +8% | **SAME** | v0.4 只補充說明；現行：ESSBElem3.AstralHitMult；Papyrus 直讀：ESSBController×1、ESSBElem3×1 |
|  | 大師 | 主線 | 同調每段星附傷 +1%／點 | DLL N2 | `ESSB_P_astral_0_3_M1..M15` 0x0048F7–0x004905 | 同調每段星附傷 +1%／點 | **SAME** | 現行：ESSBElem3.AstralHitMult；Papyrus 共用：ESSBController.NativeNodeSum（N2 鏡像）；**DLL：kProcMaster[elem]** |
|  |  | 分支 1 | **餘輝**：闇宙用完回到一般形態時，立即得到 3 層共鳴層 | DLL N4 | （無） | — | **NEW** | 闇宙用完得 3 層共鳴層；— |
|  |  | （移除） | — | — | `ESSB_P_astral_0_3_B1` 0x002264 | 預知：星痕引爆前 1 秒你受傷 -20% | **REMOVED** | 引爆前 1 秒受傷 -20%（PERK 0x24，讀 GuardAstral）；現行：ESSBElem3.AstralForesee ← ESSBStatus.Tick + PERK ESSB_P_astr…；Papyrus 直讀：ESSBElem3×1；ESP 進入點：0x24 |
|  |  | （移除） | — | — | `ESSB_P_astral_0_3_B2` 0x002265 | 星盾：星痕引爆時你獲得小護盾 | **REMOVED** | 引爆時小護盾；現行：ESSBElem3.OnAstralDetonate；Papyrus 直讀：ESSBElem3×1 |
|  | 傳奇 | 主線 | 永夜，闇星每一擊 +3%／點 | DLL N4 | `ESSB_P_astral_0_4_M1..M15` 0x004906–0x004914 | 群星：同調三段時星落連鎖附近星痕目標，範圍 1 公尺 +1 公尺／點（滿點 16 公尺） | **CHANGED** | 群星（星落連鎖範圍）→ 永夜（闇星每擊 +3%）；現行：ESSBElem3.FallChain / ConstellationRadius；Papyrus 直讀：ESSBElem3×2 |
|  |  | 分支 1 | **星蝕**：闇星中每一擊的傷害，另以 50% 回聲到所有其他共鳴目標（最多 5） | DLL N5 | （無） | — | **NEW** | 闇星每擊 50% 回聲；— |
|  |  | 分支 2 | **天穹**：同調三段時升闇星的門檻 10 → 7 | DLL N4 | （無） | — | **NEW** | 升闇星門檻 10 → 7；— |
|  |  | （移除） | — | — | `ESSB_P_astral_0_4_B1` 0x002268 | 星體：同調三段時魔法傷害 -30%，星痕引爆治療你 | **REMOVED** | 同調三段魔傷 -30%（PERK 0x29）；現行：ESSBElem3.OnAstralDetonate + PERK ESSB_P_astral_0_4_B1 進入點 0…；Papyrus 直讀：ESSBElem3×1；ESP 進入點：0x29 |
| 開啟（星臨） | 新手 | 主線 | 星痕延遲 -0.1 秒／點（2 → 0.5 秒） | DLL N3 | `ESSB_P_astral_1_0_M1..M15` 0x004915–0x004923 | 星痕延遲 -0.1 秒／點 | **SAME** | v0.4 只補充說明；現行：ESSBElem3.AstralDelay → ESSBStatus.Tick；Papyrus 直讀：ESSBElem3×1 |
|  |  | 分支 1 | **星散**：開印時附近 1 人也星痕（也進入共鳴） | DLL N3（掃描 N5） | `ESSB_P_astral_1_0_B1` 0x00226C | 星散：開印時附近 1 人也星痕，搜尋範圍隨星臨主線成長 | **RETUNED** | 拿掉「搜尋範圍隨主線成長」，加上進入共鳴；現行：ESSBElem3.OpenAstral / ScatterRadius；Papyrus 直讀：ESSBElem3×1 |
|  | 熟練 | 主線 | 開印後 5 秒內星附傷 +1%／點 | DLL N3 | `ESSB_P_astral_1_1_M1..M15` 0x004924–0x004932 | 開印後 5 秒內星附傷 +1%／點 | **SAME** | 現行：ESSBElem3.AstralHitMult（GetOpenBoost）；Papyrus 直讀：ESSBElem3×1；Papyrus 共用：ESSBController.DifferencePossible／開印加成 |
|  |  | 分支 1 | **明星**：開印時若 15 公尺內已有其他共鳴目標，新目標與最近的那一個星痕各 +1 | DLL N3（掃描 N5） | `ESSB_P_astral_1_1_B1` 0x002270 | 明星：開印那一擊附傷 ×1.5 | **CHANGED** | 開印 ×1.5 → 附近共鳴時兩邊星痕 +1；現行：ESSBElem.OpenStrikeMult；Papyrus 共用：ESSBElem.OpenStrikeMult ×1.5＋ESSBController.DifferencePossible（各元素共用） |
|  |  | （移除） | — | — | `ESSB_P_astral_1_1_B2` 0x002271 | 星引力：開印時回復魔力 | **REMOVED** | 開印回魔；現行：ESSBElem3.OpenAstral；Papyrus 直讀：ESSBElem3×1 |
|  | 專精 | 主線 | 星印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_astral_1_2_M1..M15` 0x004933–0x004941 | 星印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBElem.MarkDurationBonus；Papyrus 共用：ESSBElem.MarkDurationBonus |
|  |  | 分支 1 | **星臨強化**：星臨時範圍內敵人星痕 2 層（全部進入共鳴） | Papyrus＋DLL N5 | `ESSB_P_astral_1_2_B1` 0x002274 | 星臨強化：星臨時範圍內敵人星痕 2 層 | **SAME** | v0.4 只補充說明；現行：ESSBElem3.OnFormOpened(11)；Papyrus 直讀：ESSBElem3×1 |
|  | 大師 | 主線 | 星臨，開星形態時對範圍內敵人各開印一次，範圍 2 公尺 +0.2 公尺／點 | Papyrus＋DLL N5 | `ESSB_P_astral_1_3_M1..M15` 0x004942–0x004950 | 星臨：開星形態時對範圍內敵人各開印一次，範圍 2 公尺 +1 公尺／點（滿點 17 公尺） | **RETUNED** | 範圍 +1 公尺／點 → +0.2 公尺／點（對齊各元素 X 臨）；現行：ESSBElem.OnFormOpened → ESSBElem3.AdventRadius；Papyrus 直讀：ESSBElem3×2；Papyrus 共用：ESSBElem.OnFormOpened（X 臨） |
|  |  | 分支 1 | **星鎖**：開印目標 3 秒內受所有元素傷 +10% | DLL N3＋引擎效果 | `ESSB_P_astral_1_3_B1` 0x002278 | 星鎖：開印目標 3 秒內受所有元素傷 +10% | **SAME** | 現行：ESSBElem3.OpenAstral → ESSBController.SetStarLock → ESSBElem…；Papyrus 直讀：ESSBController×1、ESSBElem3×2 |
|  |  | 分支 2 | **星門**：開印時你 +1 共鳴層（闇星中無效） | DLL N4 | （無） | — | **NEW** | 開印 +1 共鳴層；— |
|  |  | （移除） | — | — | `ESSB_P_astral_1_3_B2` 0x002279 | 星光：開印時你受傷 -10% 3 秒 | **REMOVED** | 開印受傷 -10%（PERK 0x24，讀 GuardStar）；現行：ESSBElem3.OpenAstral + PERK ESSB_P_astral_1_3_B2 進入點 0x24；Papyrus 直讀：ESSBElem3×1；ESP 進入點：0x24 |
|  | 傳奇 | 主線 | 開印效果 +3%／點 | DLL N3 | `ESSB_P_astral_1_4_M1..M15` 0x004951–0x00495F | 開印效果 +3%／點 | **SAME** | 現行：ESSBElem.OpenMult；Papyrus 共用：ESSBElem.OpenMult |
|  |  | 分支 1 | **星耀**：同調三段時開印的延遲星傷改為立即並 ×2（這次引爆照常給共鳴層） | DLL N3 | `ESSB_P_astral_1_4_B1` 0x00227C | 星耀：同調三段時開印的延遲星傷改為立即並 ×2 | **SAME** | v0.4 只補充說明；現行：ESSBElem3.OpenAstral；Papyrus 直讀：ESSBElem3×1 |
| 關閉（星落） | 新手 | 主線 | 終焉 +2%／點 | DLL N3（融斷 N5） | `ESSB_P_astral_2_0_M1..M15` 0x004960–0x00496E | 終焉 +2%／點 | **SAME** | 現行：ESSBElem.EndMult；Papyrus 共用：ESSBElem.EndMult |
|  |  | 分支 1 | **隕星**：星落 ×2.0 → ×3.0 | DLL N3 | `ESSB_P_astral_2_0_B1` 0x002280 | 隕星：星落 ×2.0 → ×3.0 | **SAME** | 現行：ESSBElem3.FallK；Papyrus 直讀：ESSBElem3×1 |
|  | 熟練 | 主線 | 星印記的融斷 +2%／點 | DLL N5 | `ESSB_P_astral_2_1_M1..M15` 0x00496F–0x00497D | 星印記的融斷 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **星斷**：星印記融斷改為真實傷害，倍率 ×0.6 | DLL N5 | `ESSB_P_astral_2_1_B2` 0x002285 | 星斷：星印記融斷改為真實傷害，倍率 ×0.6 | **SAME** | 現行：ESSBElem3.Fall → ESSBController.ApplyTrueDamage(amount, targ…；Papyrus 直讀：ESSBElem3×1 |
|  |  | （移除） | — | — | `ESSB_P_astral_2_1_B1` 0x002284 | 流星雨：星落改為範圍（基礎 3 公尺，隨關閉專精主線成長） | **REMOVED** | 星落範圍化（星不再以範圍為身分）；現行：ESSBElem3.HasMeteorShower / FallRadius；Papyrus 直讀：ESSBElem3×1 |
|  | 專精 | 主線 | 終焉後 5 秒內接管元素附傷 +1%／點 | DLL N3 | `ESSB_P_astral_2_2_M1..M15` 0x00497E–0x00498C | 星落與星域的範圍 +0.8 公尺／點（3 → 15 公尺；星落需「流星雨」才有範圍） | **CHANGED** | 星落／星域範圍 → 終焉後接管元素附傷（對齊骨架）；現行：ESSBElem3.FallRadius；Papyrus 直讀：ESSBElem3×1；Papyrus 共用：ESSBElem（SetEndBoost，任何樹這格有點數都會觸發） |
|  |  | 分支 1 | **星殘**：離開星形態（切換或 Z）時共鳴層不清空，保留 15 秒；15 秒內回到星形態就接著集 | Papyrus＋DLL N4 | （無） | — | **NEW** | 離開星形態保留共鳴層 15 秒；— |
|  |  | （移除） | — | — | `ESSB_P_astral_2_2_B1` 0x002288 | 星引：星終焉後接管元素 +10 同調 | **REMOVED** | 接管元素 +10 同調；現行：ESSBElem3.EndAstralNodes → ESSBController.AddSync(10)；Papyrus 直讀：ESSBElem3×1 |
|  | 大師 | 主線 | 星印記的融斷再 +2%／點 | DLL N5 | `ESSB_P_astral_2_3_M1..M15` 0x00498D–0x00499B | 星印記的融斷再 +2%／點 | **SAME** | 現行：ESSBElem.BurstMult；Papyrus 共用：ESSBElem.BurstMult |
|  |  | 分支 1 | **墜星**：闇星中切換時剩下的闇宙留到被切那一擊，每層對該目標結算一次 ×0.5 闇星一擊；闇星中按 Z 時，剩下的闇宙平均分給範圍內帶星印記的目標，同樣每層 ×0.5 | DLL N4（融斷 N5） | （無） | — | **NEW** | 闇星中切換／融斷結算剩餘闇宙；— |
|  |  | （移除） | — | — | `ESSB_P_astral_2_3_B1` 0x00228C | 星界之門：星終焉後接管元素直接視為同調一段 | **REMOVED** | 接管元素視為同調一段；現行：ESSBElem3.EndAstralNodes → ESSBController.BoostSyncToStage1；Papyrus 直讀：ESSBElem3×1 |
|  |  | （移除） | — | — | `ESSB_P_astral_2_3_B2` 0x00228D | 星軌終焉：星終焉後接管元素的開印 ×1.5 | **REMOVED** | 接管元素開印 ×1.5；現行：ESSBElem3.TakeoverOpenMult → ESSBReactions.EndAstral；Papyrus 直讀：ESSBElem3×1 |
|  | 傳奇 | 主線 | 星落 +3%／點 | DLL N3（融斷 N5） | `ESSB_P_astral_2_4_M1..M15` 0x00499C–0x0049AA | 星落 +3%／點 | **SAME** | 現行：ESSBElem.SignatureMult → ESSBElem3.Fall；Papyrus 共用：ESSBElem.SignatureMult |
|  |  | 分支 1 | **星域**：星印記融斷後留下 5 秒星域（3 公尺），內部敵人受所有元素傷 +20% | Papyrus（領域） | `ESSB_P_astral_2_4_B1` 0x002290 | 星域：星印記融斷後留下 5 秒星域，範圍同星落，內部敵人受所有元素傷 +20% | **RETUNED** | 範圍同星落 → 固定 3 公尺；現行：ESSBElem3.EndAstralNodes → ESSBController.StartDomain(11, 5,…；Papyrus 直讀：ESSBController×1、ESSBElem3×2 |

### 5.1 無元素（`noform`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 大師 | 新手 | 主線 | 吸魔量 +5%／點（不吃節點倍率；×1.0 → ×1.75） | DLL N2 | `ESSB_P_noform_0_0_M1..M15` 0x0049AB–0x0049B9 | 無形態時武器傷害 +1%／點 | **CHANGED** | 無形態武器傷害（現有 PERK 0x23 ×15 階＋RefreshWeaponPercent 寫入）→ 吸魔量 +5%；現行：PERK ESSB_P_noform_0_0_M<n> 進入點 0x23（武器傷害）；Papyrus 直讀：ESSBNodes(GetMainPerk+SetNthEntryValue)×1；ESP 進入點：PERK 0x23（武器傷害） |
|  |  | 分支 1 | **逼近**：15 公尺內的敵人施法時，你 2 秒內移速 +30%，這 2 秒內化法為力的回魔比例加倍（頂著法術衝上去），每 6 秒一次 | DLL N4（施法事件）＋引擎效果 | （無） | — | **NEW** | 附近敵人施法時移速＋化法為力加倍（DLL 施法事件）；— |
|  |  | （移除） | — | — | `ESSB_P_noform_0_0_B1` 0x002294 | 穩步：格擋耐力消耗 -20% | **REMOVED** | 格擋耐力 -20%（本來就 DEFERRED，無進入點）；現行：PERK ESSB_P_noform_0_0_B1（目前無進入點） |
|  | 熟練 | 主線 | 超載上限 +2%／點（+50% → +80%） | DLL N4 | `ESSB_P_noform_0_1_M1..M15` 0x0049BA–0x0049C8 | 重擊碎甲：自有減防 1%／點，5 秒 | **CHANGED** | 重擊碎甲 → 超載上限；現行：ESSBNoForm.OnMartialHit；Papyrus 直讀：ESSBNoForm×1 |
|  |  | 分支 1 | **蓄流**：超載開始衰減前的等待 3 → 6 秒 | DLL N4 | （無） | — | **NEW** | 超載衰減等待 3 → 6 秒；— |
|  |  | 分支 2 | **反擊**：格擋成功後 3 秒內下一次命中吸魔 ×2 | DLL 受擊 N4＋DLL N2 | `ESSB_P_noform_0_1_B1` 0x002298 | 反擊：格擋成功後 3 秒內下一次命中傷害 +30% | **CHANGED** | 下一擊傷害 +30% → 下一擊吸魔 ×2；v0.4 表序從第 1 格變第 2 格；現行：ESSBGuard.OnHitEx（abHitBlocked）→ ESSBController.SetRiposte |
|  |  | （移除） | — | — | `ESSB_P_noform_0_1_B2` 0x002299 | 疾攻：連續命中每次重擊耐力消耗 -10%，最多 -50% | **REMOVED** | 重擊耐力遞減（PERK 0x1B ×5 段）；現行：PERK ESSB_P_noform_0_1_B2 進入點 0x1B（重擊耐力）×5；ESP 進入點：0x1B×5 |
|  | 專精 | 主線 | 法盾效率，每擋 1 點花的魔力 -2%／點（最多 -30%：1.0 → 0.7，超載 0.75 → 0.53） | DLL 受擊 N4 | `ESSB_P_noform_0_2_M1..M15` 0x0049C9–0x0049D7 | 無形態時暴擊率 +1%／點（自有判定） | **CHANGED** | 暴擊率 → 法盾效率；現行：ESSBNoForm.OnMartialHit；Papyrus 直讀：ESSBNoForm×1 |
|  |  | 分支 1 | **化勁**：化法為力的回魔比例 30% → 60% | DLL 受擊 N4 | （無） | — | **NEW** | 化法為力回魔 30 → 60%；— |
|  |  | （移除） | — | — | `ESSB_P_noform_0_2_B1` 0x00229C | 節奏：4 秒內連續命中 3 次，回復耐力並 +1 戰意（最多 5） | **REMOVED** | 連擊回耐＋戰意；現行：ESSBNoForm.OnCombo → ESSBController.OnNoFormHit；Papyrus 直讀：ESSBNoForm×1 |
|  | 大師 | 主線 | 法盾分擔 +1%／點（30% → 45%；超載 45% → 60%） | 引擎效果（PERK） | `ESSB_P_noform_0_3_M1..M15` 0x0049D8–0x0049E6 | 戰意：每層武器傷害 +0.5%／點 | **CHANGED** | 戰意每層武器傷害（現有 PERK 0x23 ×5 段×15 階＋RefreshWeaponPercent 寫 5 個進入點）→ 法盾分擔 +1%（引擎效果 PERK）；現行：PERK ESSB_P_noform_0_3_M<n> 進入點 0x23 ×5；Papyrus 直讀：ESSBNodes(GetMainPerk+SetNthEntryValue)×1；ESP 進入點：PERK 0x23 ×5 段 |
|  |  | 分支 1 | **不屈**：被命中時戰意 +1（每 3 秒一次），並重設戰意歸零計時 | DLL 受擊 N4 | `ESSB_P_noform_0_3_B2` 0x0022A1 | 不屈：戰意 ≥3 時受傷 -10% | **CHANGED** | 戰意 ≥3 受傷 -10%（現有 PERK 0x24）→ 被命中戰意 +1；表序第 2 格變第 1 格；現行：PERK ESSB_P_noform_0_3_B2 進入點 0x24；ESP 進入點：0x24 |
|  |  | 分支 2 | **餘魔**：法盾把魔力扣到 0 的那一刻不中斷，再以 30% 分擔 2 秒（改扣耐力），每 30 秒一次 | DLL 受擊 N4＋引擎效果 | （無） | — | **NEW** | 法盾扣到 0 後改扣耐力 2 秒；— |
|  |  | （移除） | — | — | `ESSB_P_noform_0_3_B1` 0x0022A0 | 破勢：碎甲持續改為 8 秒 | **REMOVED** | 碎甲 8 秒；現行：ESSBNoForm.OnMartialHit；Papyrus 直讀：ESSBNoForm×1 |
|  | 傳奇 | 主線 | 不竭，超載衰減每秒 -0.2%／點（5% → 2%） | DLL N4 | `ESSB_P_noform_0_4_M1..M15` 0x0049E7–0x0049F5 | 終結：戰意滿層重擊無視護甲 +3%／點 | **CHANGED** | 戰意滿層重擊無視護甲 → 不竭（超載衰減）；現行：ESSBNoForm.OnMartialHit（真實傷害路徑）；Papyrus 直讀：ESSBNoForm×2 |
|  |  | 分支 1 | **破式**：戰意滿層時的重擊消耗全部戰意，這一次滅法不花你的魔力（X 照算），倍率 +1.0，並沉默目標 2 秒 | DLL N4 | （無） | — | **NEW** | 戰意滿層重擊免費滅法；— |
|  |  | 分支 2 | **無魔**：擊殺施法者回滿耐力與魔力（溢出進超載） | DLL N5 | （無） | — | **NEW** | 從 滅法‧傳奇 搬來（v0.3 ESSB_P_noform_1_4_B1），另加「溢出進超載」；跨階搬移，FormID 必然不同；— |
|  |  | （移除） | — | — | `ESSB_P_noform_0_4_B1` 0x0022A4 | 處決：戰意滿層時重擊對低於 25% 生命的目標傷害 ×3，消耗全部戰意 | **REMOVED** | 處決只在冰；現行：ESSBNoForm.OnMartialHit；Papyrus 直讀：ESSBNoForm×1 |
| 滅法 | 新手 | 主線 | 滅法倍率 +2%／點（不吃節點倍率；×1.0 → ×1.3，超載 ×1.5 → ×1.8） | DLL N2 | `ESSB_P_noform_1_0_M1..M15` 0x0049F6–0x004A04 | 破魔：命中削減目標魔力 5（+1／點），回復你等量魔力，造成削減量 ×0.5 的真實傷害（無視護甲與所有抗性），並施加「破魔印」8 秒 | **CHANGED** | 破魔（削魔＋真傷＋破魔印，已搬成基礎吸魔／小滅法）→ 滅法倍率 +2%；現行：ESSBNoForm.OnManaBreak |
|  |  | 分支 1 | **奪魔**：吸魔量改為「固定值」與「目標最大魔力 10%」取高者 | DLL N2 | `ESSB_P_noform_1_0_B1` 0x0022A8 | 蝕魔：削魔量改為「固定值」與「目標最大魔力 2%」取高者 | **RETUNED** | 改名；削魔 → 吸魔，settings 已是 10%（native kNoFormSeize）；現行：ESSBNoForm.OnManaBreak；**DLL：kNoFormSeize** |
|  | 熟練 | 主線 | 燒魔倍數 +7%／點（Y 最多是 X 的 1.0 → 2.05 倍） | DLL N2 | `ESSB_P_noform_1_1_M1..M15` 0x004A05–0x004A13 | 真實傷害比例 +3%／點（0.5 → 0.95） | **CHANGED** | 真實傷害比例 → 燒魔倍數（native 目前 kBurnMultiple 寫死 1.0，註明「這條主線還不存在」）；現行：ESSBNoForm.OnManaBreak |
|  |  | 分支 1 | **斷咒**：命中施法中的敵人打斷其施法，每 5 秒一次；成功時戰意 +1 | DLL N4 | `ESSB_P_noform_1_1_B1` 0x0022AC | 斷咒：命中施法中的敵人打斷其施法，每 5 秒一次 | **RETUNED** | 加上戰意 +1；現行：ESSBNoForm.IsCasting + ESSBController.TakeInterrupt；Papyrus 直讀：ESSBController×1、ESSBNoForm×1 |
|  |  | 分支 2 | **反咒**：帶滅法印的敵人施法時，受其該次施法消耗魔力 100% 的真實傷害（每無元素樹等級 +2%，100 級為 300%），戰意 +1 | DLL N4 | `ESSB_P_noform_1_1_B3` 0x0022AE | 反咒：帶破魔印的敵人施法時，受其該次施法消耗魔力 100% 的真實傷害；每無元素樹等級 +2%，100 級為 300% | **RETUNED** | 破魔印 → 滅法印，加戰意 +1；表序第 3 格變第 2 格；現行：ESSBCounter.OnAnimationEvent → ESSBNoForm.OnCounterSpell；Papyrus 直讀：ESSBController×1、ESSBNoForm×1 |
|  |  | （移除） | — | — | `ESSB_P_noform_1_1_B2` 0x0022AD | 反噬：受到法術傷害時回復魔力 | **REMOVED** | 併入基礎「化法為力」；現行：ESSBGuard.OnHitEx（akSource 是 Spell） |
|  | 專精 | 主線 | 沉默 +0.2 秒／點（1 → 4 秒） | DLL N2 | `ESSB_P_noform_1_2_M1..M15` 0x004A14–0x004A22 | 沉默：目標魔力被削至 0 時施加沉默 1 秒（+0.2 秒／點，最長 4 秒）；沉默中無法施法、不回復魔力 | **RETUNED** | 沉默本身搬進基礎滅法，主線只剩 +0.2 秒／點（native kNoFormSilence）；現行：ESSBNoForm.ApplySilence → ESSBController.ApplySilenceSpell；**DLL：kNoFormSilence** |
|  |  | 分支 1 | **枯竭**：目標沒有魔力時，滅法改為燒你自己 2 倍的 X 並照算入傷害（打野獸、亡靈的補救） | DLL N2 | `ESSB_P_noform_1_2_B1` 0x0022B0 | 枯竭：目標魔力已為 0 時，真實傷害改以你當前魔力的 5% 計 | **CHANGED** | 改以你當前魔力 5% 計真傷 → 燒你自己 2 倍 X；現行：ESSBNoForm.OnManaBreak；**DLL：kNoFormDepletion** |
|  |  | 分支 2 | **靜寂**：沉默中的目標受真實傷害 ×1.5 | DLL N2 | `ESSB_P_noform_1_2_B2` 0x0022B1 | 靜寂：沉默中的目標受真實傷害 ×1.5 | **SAME** | 現行：ESSBNoForm.OnManaBreak（ESSB_Silence keyword）；**DLL：kNoFormStillness** |
|  | 大師 | 主線 | 對施法者與帶魔法護盾、元素披風的敵人燒魔 +5%／點 | DLL N2 | `ESSB_P_noform_1_3_M1..M15` 0x004A23–0x004A31 | 對施法者與帶魔法護盾、元素披風的敵人削魔量 +5%／點 | **RETUNED** | 削魔量 → 燒魔量（native kNoFormBurnCasters）；現行：ESSBNoForm.IsSpellUser；**DLL：kNoFormBurnCasters** |
|  |  | 分支 1 | **破護**：不受元素披風反傷（第一跳仍會吃到） | DLL 受擊 N4 | `ESSB_P_noform_1_3_B1` 0x0022B4 | 破護：不受元素披風反傷 | **SAME** | v0.4 只補充說明；現行：ESSBGuard.OnHitEx + PERK ESSB_P_noform_1_3_B1 進入點 0x29；ESP 進入點：0x29 |
|  |  | 分支 2 | **咒返**：受到法術傷害時，對施法者施加滅法印（它的下一次施法就吃反咒），每 5 秒一次 | DLL 受擊 N4 | （無） | — | **NEW** | 受法術傷害時給施法者掛滅法印；— |
|  |  | （移除） | — | — | `ESSB_P_noform_1_3_B2` 0x0022B5 | 抗咒：無形態時魔抗 +15% | **REMOVED** | 無形態魔抗 +15%（自有常駐能力，ESSBController 的 AntiMagicAbility 屬性）；現行：SPEL ESSB_Ability_AntiMagic + ESSBController.RefreshAbilitie…；Papyrus 直讀：ESSBController×1 |
|  | 傳奇 | 主線 | 目標魔力低於 25% 時命中傷害 +3%／點 | DLL N2 | `ESSB_P_noform_1_4_M1..M15` 0x004A32–0x004A40 | 目標魔力低於 25% 時命中傷害 +3%／點 | **SAME** | 現行：ESSBNoForm.TrueMult；Papyrus 直讀：ESSBNoForm×1；**DLL：kNoFormLowMagicka** |
|  |  | 分支 1 | **噬命**：真實傷害的 50% 轉為你的生命 | DLL N2 | `ESSB_P_noform_1_4_B2` 0x0022B9 | 逆流：真實傷害的 50% 轉為你的生命 | **RETUNED** | 改名，效果相同（native kNoFormDevour）；表序第 2 格變第 1 格；現行：ESSBController.ApplyTrueDamage；Papyrus 直讀：ESSBController×1；**DLL：kNoFormDevour** |
|  |  | 分支 2 | **封印**：沉默改為 3 公尺範圍 | DLL N5 | `ESSB_P_noform_1_4_B3` 0x0022BA | 封印：沉默改為 3 公尺範圍 | **SAME** | 現行：ESSBNoForm.ApplySilence |
|  |  | （移除） | — | — | `ESSB_P_noform_1_4_B1` 0x0022B8 | 無魔：擊殺施法者回滿耐力與魔力 | **REMOVED** | 搬到 大師‧傳奇（見該列 NEW）；現行：ESSBNoForm.OnKill → ESSBController.Tick；Papyrus 直讀：ESSBNoForm×1 |
| 冷寂 | 新手 | 主線 | 融斷 +2%／點 | DLL N5 | `ESSB_P_noform_2_0_M1..M15` 0x004A41–0x004A4F | 融斷 +2%／點 | **SAME** | 現行：ESSBNoForm.BurstMult；Papyrus 直讀：ESSBNoForm×1 |
|  |  | 分支 1 | **免門檻**：融斷後下一次開形態不需魔力 | Papyrus | `ESSB_P_noform_2_0_B1` 0x0022BC | 免門檻：融斷後下一次開形態不需魔力 | **SAME** | 現行：ESSBNoForm.OnBurst → ESSBController.ToggleForm；Papyrus 直讀：ESSBNoForm×1 |
|  | 熟練 | 主線 | 寂每層燒魔 +0.5%／點（5% → 12.5%） | DLL N5 | `ESSB_P_noform_2_1_M1..M15` 0x004A50–0x004A5E | 餘燼：關閉形態後 10 秒內無形態命中附帶前一元素附傷 +2%／點 | **CHANGED** | 餘燼（關形態後附前元素附傷）→ 寂每層燒魔；現行：ESSBNoForm.EmberRatio → ESSBController.OnNoFormHit；Papyrus 直讀：ESSBNoForm×2 |
|  |  | 分支 1 | **收束**：融斷範圍 15 → 20 公尺 | DLL N5 | `ESSB_P_noform_2_1_B1` 0x0022C0 | 收束：融斷範圍 15 → 20 公尺 | **SAME** | 現行：ESSBNoForm.BurstRadius；Papyrus 直讀：ESSBNoForm×1 |
|  |  | 分支 2 | **寂滅**：寂 ≥3 層的目標，你對它的下一次滅法倍率 +0.5 | DLL N2 | （無） | — | **NEW** | 寂 ≥3 下一次滅法倍率 +0.5；— |
|  |  | （移除） | — | — | `ESSB_P_noform_2_1_B2` 0x0022C1 | 餘燼延續：餘燼改為 20 秒 | **REMOVED** | 主線「餘燼」已移除；現行：ESSBNoForm.OnBurst；Papyrus 直讀：ESSBNoForm×1 |
|  | 專精 | 主線 | 融斷範圍 +0.3 公尺／點 | DLL N5 | `ESSB_P_noform_2_2_M1..M15` 0x004A5F–0x004A6D | 融斷範圍 +0.3 公尺／點 | **SAME** | 現行：ESSBNoForm.BurstRadius；Papyrus 直讀：ESSBNoForm×1 |
|  |  | 分支 1 | **連斷**：融斷後 5 秒內重開任一形態，保留一半同調 | Papyrus＋DLL N4 | `ESSB_P_noform_2_2_B1` 0x0022C4 | 連斷：融斷後 5 秒內重開任一形態，保留一半同調 | **SAME** | 現行：ESSBNoForm.OnBurst → ESSBController.SetSyncKeep；Papyrus 直讀：ESSBNoForm×1 |
|  | 大師 | 主線 | 寂上限 +1／每 5 點（5 → 8） | DLL N5 | `ESSB_P_noform_2_3_M1..M15` 0x004A6E–0x004A7C | 淬火：融斷後 10 秒內武器傷害 +1%／點 | **CHANGED** | 淬火（融斷後武器傷害，現有 PERK 0x23＋RefreshWeaponPercent）→ 寂上限；現行：PERK ESSB_P_noform_2_3_M<n> 進入點 0x23；Papyrus 直讀：ESSBNoForm×1、ESSBNodes(GetMainPerk+SetNthEntryValue)×1；ESP 進入點：PERK 0x23 |
|  |  | 分支 1 | **斷界**：融斷後對範圍內敵人施加所有被結清元素的弱化 3 秒 | DLL N5 | `ESSB_P_noform_2_3_B1` 0x0022C8 | 斷界：融斷後對範圍內敵人施加所有被結清元素的弱化 3 秒 | **SAME** | 現行：ESSBNoForm.OnBurstTarget；Papyrus 直讀：ESSBNoForm×1 |
|  |  | 分支 2 | **回流**：融斷回復你魔力，每個印記 B_max ×0.5（可以灌進超載） | DLL N5 | `ESSB_P_noform_2_3_B2` 0x0022C9 | 回流：融斷回復你魔力，每個印記 B_max ×0.5 | **SAME** | v0.4 只補充說明；現行：ESSBNoForm.OnBurst；Papyrus 直讀：ESSBNoForm×1 |
|  | 傳奇 | 主線 | 融斷再 +3%／點 | DLL N5 | `ESSB_P_noform_2_4_M1..M15` 0x004A7D–0x004A8B | 融斷再 +3%／點 | **SAME** | 現行：ESSBNoForm.BurstMult；Papyrus 直讀：ESSBNoForm×1 |
|  |  | 分支 1 | **雙斷**：融斷後 3 秒內再次按 Z 開任一形態，會對範圍內敵人立即開印一次 | Papyrus＋DLL N5 | `ESSB_P_noform_2_4_B1` 0x0022CC | 雙斷：融斷後 3 秒內再次按 Z 開任一形態，會對範圍內敵人立即開印一次 | **SAME** | 現行：ESSBNoForm.OnBurst → ESSBController.OnFormOpened；Papyrus 直讀：ESSBNoForm×1 |
|  |  | 分支 2 | **萬寂**：融斷時寂 ≥3 層的目標身上其他元素狀態（凍結、詛咒、血痕、中毒、水壓、星痕等）全部清除，每清一種寂 +1，並轉為一次「該元素 B_max ×0.5」的真實傷害 | DLL N5 | （無） | — | **NEW** | 融斷清狀態換寂與真傷；— |

### 5.2 全元素通用（`common`）

| 路線 | 階 | 節點 | v0.4 效果 | v0.4 負責 | 現有 perk（EditorID／FormID） | 現有效果（v0.3 基準值） | 分類 | 備註與接線 |
|---|---|---|---|---|---|---|---|---|
| 持續 | 新手 | 主線 | 同調門檻 -2%／點 | DLL N4 | `ESSB_P_common_0_0_M1..M15` 0x004A8C–0x004A9A | 同調門檻 -2%／點 | **SAME** | 現行：ESSBNodes.SyncThresholdScale → ESSBController.SyncStage；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 1 | **承接**：切換時保留前一形態三分之一同調 | Papyrus＋DLL N4 | `ESSB_P_common_0_0_B1` 0x0022D0 | 承接：切換時保留前一形態三分之一同調 | **SAME** | 現行：ESSBNodes.CarryOverSync → ESSBController.SwitchForm；Papyrus 直讀：ESSBNodes×1 |
|  | 熟練 | 主線 | 同調二段時附傷 +1%／點 | DLL N2 | `ESSB_P_common_0_1_M1..M15` 0x004A9B–0x004AA9 | 同調二段時附傷 +1%／點 | **SAME** | 現行：ESSBNodes.CommonHitMult；Papyrus 直讀：ESSBNodes×1；**DLL：kCommonStage2** |
|  |  | 分支 1 | **不移**：同調二段以上時免疫硬直與擊倒（自有，可調） | 引擎效果 | `ESSB_P_common_0_1_B1` 0x0022D4 | 不移：被打斷或擊倒不失去同調 | **CHANGED** | 不失同調（行為保證）→ 免疫硬直與擊倒（引擎效果）；現行：ESSBController（同調只在切換與關閉時歸零） |
|  |  | 分支 2 | **專一**：同一形態持續超過 60 秒後同調門檻再降一半 | 引擎效果（60 秒效果）＋DLL N4 | `ESSB_P_common_0_1_B2` 0x0022D5 | 專一：同一形態持續超過 60 秒後同調門檻再降一半 | **SAME** | 現行：ESSBNodes.SyncThresholdScale + ESSBController.FormHeldSecond…；Papyrus 直讀：ESSBNodes×1 |
|  | 專精 | 主線 | 同調三段時終焉 +1%／點 | DLL N3（融斷 N5） | `ESSB_P_common_0_2_M1..M15` 0x004AAA–0x004AB8 | 同調三段時受傷 -0.5%／點 | **CHANGED** | 同調三段受傷 -0.5%（現有 PERK 0x24 ×15 階）→ 同調三段終焉 +1%；現行：PERK ESSB_P_common_0_2_M<n> 進入點 0x24（受到的傷害）；ESP 進入點：PERK 0x24（受到的傷害） |
|  |  | 分支 1 | **定神**：同調三段時免疫減速（自有） | 引擎效果 | `ESSB_P_common_0_2_B1` 0x0022D8 | 定神：同調三段時免疫減速（自有） | **SAME** | 現行：ESSBNodes.SelfSlowImmune；Papyrus 直讀：ESSBNodes×1 |
|  | 大師 | 主線 | 同調三段時重擊附傷 +2%／點 | DLL N2 | `ESSB_P_common_0_3_M1..M15` 0x004AB9–0x004AC7 | 同調三段時重擊附傷 +2%／點 | **SAME** | 現行：ESSBNodes.CommonHitMult；Papyrus 直讀：ESSBNodes×1；**DLL：kCommonStage3Power** |
|  |  | 分支 1 | **極致**：同調三段時每 10 次命中額外一次全額附傷 | DLL N4 | `ESSB_P_common_0_3_B1` 0x0022DC | 極致：同調三段時每 10 次命中額外一次全額附傷 | **SAME** | 現行：ESSBController.OnWeaponHit（ExtremeCount）；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 2 | **回饋**：同調升段時回復生命與魔力各 B_max ×2 | DLL N4 | `ESSB_P_common_0_3_B2` 0x0022DD | 回饋：同調升段時回復生命與魔力各 B_max ×2 | **SAME** | 現行：ESSBNodes.OnSyncStage；Papyrus 直讀：ESSBNodes×1 |
|  | 傳奇 | 主線 | 化身，同調三段時 30 秒冷卻（-1 秒／點）完成後的下一次命中，自動觸發當前元素的持續傳奇效果；若該效果屬於被動數值（如絕對零度、深淵），化身改為讓你在接下來 10 秒內視同已取得該效果 | DLL N4 | `ESSB_P_common_0_4_M1..M15` 0x004AC8–0x004AD6 | 化身：同調三段時每 30 秒自動觸發一次當前元素的持續傳奇效果，冷卻 -1 秒／點 | **RETUNED** | 化身：明寫「冷卻完成後下一次命中觸發」與被動效果改 10 秒視同取得；現行：ESSBNodes.AvatarCooldown → ESSBController.Tick → ESSBElem.On…；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 1 | **永續**：Z 關閉時若同調三段，融斷後保留一段同調到下一次開形態 | Papyrus＋DLL N4 | `ESSB_P_common_0_4_B1` 0x0022E0 | 永續：Z 關閉時若同調三段，融斷後保留一段同調到下一次開形態 | **SAME** | 現行：ESSBNodes.HasPerpetual → ESSBController.OnFormClosed；Papyrus 直讀：ESSBNodes×1 |
| 開啟 | 新手 | 主線 | 所有元素附傷 +1%／點 | DLL N2 | `ESSB_P_common_1_0_M1..M15` 0x004AD7–0x004AE5 | 所有元素附傷 +1%／點 | **SAME** | 現行：ESSBNodes.CommonHitMult；Papyrus 直讀：ESSBNodes×1；**DLL：kCommonAll1** |
|  |  | 分支 1 | **跳印**：印記自然過期時，過期終焉照常結算，然後印記跳到 6 公尺內最近一個沒有印記的敵人身上（剩 4 秒、不觸發開印），每個印記只跳一次 | DLL N3（掃描 N5） | （無） | — | **NEW** | 印記過期後跳到附近目標；— |
|  |  | （移除） | — | — | `ESSB_P_common_1_0_B1` 0x0022E4 | 廣印：開印時擴散到附近 1 人 | **REMOVED** | 開印擴散 1 人（v0.4 改由各元素開啟新手分支負責）；現行：ESSBNodes.HasWideMark → ESSBController.AfterOpen；Papyrus 直讀：ESSBNodes×1 |
|  | 熟練 | 主線 | 印記持續 +0.2 秒／點 | DLL N3 | `ESSB_P_common_1_1_M1..M15` 0x004AE6–0x004AF4 | 印記持續 +0.2 秒／點 | **SAME** | 現行：ESSBNodes.MarkDurationBonus → ESSBController.ApplyMark；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 1 | **順轉**：開形態免魔力門檻，切換後 1 秒受傷 -50% | Papyrus＋引擎效果 | `ESSB_P_common_1_1_B1` 0x0022E8 | 順轉：開形態免魔力門檻，切換後 1 秒受傷 -50% | **SAME** | 現行：ESSBController.ToggleForm + PERK ESSB_P_common_1_1_B1 進入點 0x…；Papyrus 直讀：ESSBController×1、ESSBInput×1；ESP 進入點：0x24 |
|  |  | 分支 2 | **先制**：開印時 +2 同調 | DLL N4 | `ESSB_P_common_1_1_B2` 0x0022E9 | 先制：開印時 +2 同調 | **SAME** | 現行：ESSBNodes.OpenSyncBonus → ESSBController.AfterOpen；Papyrus 直讀：ESSBNodes×1 |
|  | 專精 | 主線 | 開印時 +1 同調／每 5 點 | DLL N4 | `ESSB_P_common_1_2_M1..M15` 0x004AF5–0x004B03 | 開印時 +1 同調／每 5 點 | **SAME** | 現行：ESSBNodes.OpenSyncBonus；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 1 | **雙印**：目標可同時帶兩種元素印記，被切掉時只結算較舊的那個 | DLL N3 | `ESSB_P_common_1_2_B1` 0x0022EC | 雙印：目標可同時帶兩種元素印記，被切掉時只結算較舊的那個 | **SAME** | 現行：ESSBController.OnValidHit（RegElem2 副印記）；Papyrus 直讀：ESSBNodes×1 |
|  | 大師 | 主線 | 所有元素附傷再 +1%／點 | DLL N2 | `ESSB_P_common_1_3_M1..M15` 0x004B04–0x004B12 | 所有元素附傷再 +1%／點 | **SAME** | 現行：ESSBNodes.CommonHitMult；Papyrus 直讀：ESSBNodes×1；**DLL：kCommonAll2** |
|  |  | 分支 1 | **印潮**：切換後那一擊的開印，同時讓 15 公尺內帶著同一個舊印記的其他目標各觸發一次新元素的開印（最多 2 人；與大協奏對稱：大協奏傳終焉，印潮傳開印） | DLL N5 | （無） | — | **NEW** | 切換開印同時傳給帶舊印記的目標；— |
|  |  | 分支 2 | **臨界**：開形態那一刻附近敵人減速 30% 2 秒 | Papyrus＋DLL N5 | `ESSB_P_common_1_3_B2` 0x0022F1 | 臨界：開形態那一刻附近敵人減速 30% 2 秒 | **SAME** | 現行：ESSBNodes.OnFormOpened；Papyrus 直讀：ESSBNodes×1 |
|  |  | （移除） | — | — | `ESSB_P_common_1_3_B1` 0x0022F0 | 深印：開印那一擊附傷 ×1.5 | **REMOVED** | 開印 ×1.5（十份開印 ×1.5 全部換掉）；現行：ESSBNodes.OpenStrikeMult → ESSBController.ApplyProc；Papyrus 直讀：ESSBController×1、ESSBNodes×1 |
|  | 傳奇 | 主線 | 每種元素狀態上限 +1 層／每 5 點（最多 +3） | DLL N3／N4 | `ESSB_P_common_1_4_M1..M15` 0x004B13–0x004B21 | 每種元素狀態上限 +1 層／每 5 點 | **SAME** | v0.4 只補充說明；現行：ESSBNodes.StatusCapBonus → ESSBController.StackCap；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 1 | **萬象**：所有元素狀態的層數效果 +25% | DLL N3／N4 | `ESSB_P_common_1_4_B1` 0x0022F4 | 萬象：所有元素狀態的層數效果 +25% | **SAME** | 現行：ESSBNodes.OmniMult；Papyrus 直讀：ESSBNodes×1 |
| 關閉 | 新手 | 主線 | 終焉 +1%／點 | DLL N3（融斷 N5） | `ESSB_P_common_2_0_M1..M15` 0x004B22–0x004B30 | 終焉 +1%／點 | **SAME** | 現行：ESSBNodes.CommonEndMult；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 1 | **餘響**：切換後首次命中附帶前一元素 50% 附傷 | DLL N2 | `ESSB_P_common_2_0_B1` 0x0022F8 | 餘響：切換後首次命中附帶前一元素 50% 附傷 | **SAME** | 現行：ESSBNodes.EchoRatio → ESSBController.OnWeaponHit；Papyrus 直讀：ESSBNodes×1；**DLL：kCommonEcho** |
|  | 熟練 | 主線 | 融斷 +1%／點 | DLL N5 | `ESSB_P_common_2_1_M1..M15` 0x004B31–0x004B3F | 融斷 +1%／點 | **SAME** | 現行：ESSBNodes.CommonBurstMult；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 1 | **反哺**：每次終焉回復你 B_max 魔力 | DLL N3（融斷 N5） | `ESSB_P_common_2_1_B1` 0x0022FC | 反哺：每次終焉回復你 B_max 魔力 | **SAME** | 現行：ESSBNodes.OnEndReward；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 2 | **疊印**：終焉後舊印記保留 4 秒為副印記，Z 融斷時可再結算一次 | DLL N3 | `ESSB_P_common_2_1_B2` 0x0022FD | 疊印：終焉後舊印記保留 4 秒為副印記，Z 融斷時可再結算一次 | **SAME** | 現行：ESSBController.EndMark（RegElem2 + RegSecondUntil）；Papyrus 直讀：ESSBNodes×1 |
|  | 專精 | 主線 | 切換後首次命中附帶前一元素附傷 +3%／點 | DLL N2 | `ESSB_P_common_2_2_M1..M15` 0x004B40–0x004B4E | 切換後首次命中附帶前一元素附傷 +3%／點 | **SAME** | 現行：ESSBNodes.EchoRatio；Papyrus 直讀：ESSBNodes×1；**DLL：kCommonEchoRatio** |
|  |  | 分支 1 | **連鎖終焉**：終焉時附近帶同一印記的目標也終焉 ×0.5 | DLL N5 | `ESSB_P_common_2_2_B1` 0x002300 | 連鎖終焉：終焉時附近帶同一印記的目標也終焉 ×0.5 | **SAME** | 現行：ESSBNodes.HasChainEnd → ESSBReactions.ChainEnd；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 2 | **三重奏**：10 秒內觸發三種不同元素的終焉，第三次 ×3，且下一次融斷後保留全部同調 | DLL N3／N5 | `ESSB_P_common_2_2_B2` 0x002301 | 三重奏：10 秒內觸發三種不同元素的終焉，第三次 ×3，且下一次融斷後保留全部同調 | **SAME** | 現行：ESSBNodes.TrioMult → ESSBController.PushTrio；Papyrus 直讀：ESSBNodes×1 |
|  | 大師 | 主線 | 終焉再 +1%／點 | DLL N3（融斷 N5） | `ESSB_P_common_2_3_M1..M15` 0x004B4F–0x004B5D | 終焉再 +1%／點 | **SAME** | 現行：ESSBNodes.CommonEndMult；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 1 | **協奏**：切換後首次終焉傷害 ×1.5 | DLL N3 | `ESSB_P_common_2_3_B1` 0x002304 | 協奏：切換後首次終焉傷害 ×1.5 | **SAME** | 現行：ESSBNodes.ConcertMult → ESSBController.TakeSwitchEnd；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 2 | **安全閥**：融斷時你受傷 -50% 持續 2 秒 | 引擎效果（N5 掛上） | `ESSB_P_common_2_3_B2` 0x002305 | 安全閥：融斷時你受傷 -50% 持續 2 秒 | **SAME** | 現行：PERK ESSB_P_common_2_3_B2 進入點 0x24；Papyrus 直讀：ESSBController×1；ESP 進入點：0x24 |
|  | 傳奇 | 主線 | 融斷再 +2%／點 | DLL N5 | `ESSB_P_common_2_4_M1..M15` 0x004B5E–0x004B6C | 融斷再 +2%／點 | **SAME** | 現行：ESSBNodes.CommonBurstMult；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 1 | **大協奏**：切換後首次終焉讓範圍內帶舊印記的敵人各觸發一次該印記的終焉 | DLL N5 | `ESSB_P_common_2_4_B1` 0x002308 | 大協奏：切換後首次終焉讓範圍內帶舊印記的敵人各觸發一次該印記的終焉 | **SAME** | 現行：ESSBNodes.HasGrandConcert → ESSBReactions.ChainEnd；Papyrus 直讀：ESSBNodes×1 |
|  |  | 分支 2 | **雙生**：雙持時左手武器另附帶你前一個形態的元素 30 秒（左手同時打兩種元素），左右交替命中即交替開印終焉 | DLL N2 | `ESSB_P_common_2_4_B2` 0x002309 | 雙生：雙持時左手武器攜帶你前一個形態的元素 30 秒，左右交替命中即交替開印終焉 | **SAME** | v0.4 只補充說明（左手同時打兩種元素）；現行：ESSBNodes.HasTwin → ESSBController.OnWeaponHit（GetEquippedWe…；Papyrus 直讀：ESSBNodes×1 |

## 3. 接線說明

### 3.1 perk 怎麼產生

1. `plan_trees.py` 讀**寫死的** `元素魔戰士規劃-v0.3.md`（`PLAN = WORK / '元素魔戰士規劃-v0.3.md'`），找 `| 路線 ` 開頭且含「主線」「分支」的 4 欄表，每棵樹要剛好 15 列、每列一階，分支格用全形「／」切開、每段「名稱：說明」。v0.4 的表是 5 欄（路線／階／節點／觸發／負責）、一個節點一列、分支名加粗——**現有解析器對 v0.4 會直接失敗**，要重寫，而且 v0.3 檔案永遠不改，所以不能把 v0.4 貼回去。
2. `plan_trees.apply_balance_text` 依 `classify_main` 把純百分比主線乘上 `node_percent_scale`（寫進 DESC），並對幾個鍵（`noform 1 0`、`frost 1 0`、`water 0 1`、`water 1 0`，以及分支 蝕魔／枯竭／清流／回流）用 settings.json 的數字覆寫文字。這些鍵在 v0.4 多半換了意思（例如 `noform 1 0` 已不是破魔、`water 1 0` 已不是浸濕減速）。
3. `build_v03.apply_fix8_decisions` 對 14 個鍵（11 棵元素樹的開啟傳奇、`noform 0 4`、`blood 0 0`、`earth 2 2`）做使用者核准的縮放，最後 `assert resolved == 14`；`noform 0 4` 在 v0.4 已經是「不竭」，這個核准不再適用。
4. `build_v03.build_esp`（約 1946–1983 行）：
   - 主線：每階 15 筆 PERK，`NNAM` 串成鏈；每筆都有 CTDA「`GetGlobalValue(ESSB_Lvl_<tree>) >= 階等級`」；DESC＝「第 n/15 點：主線文字」。
   - 分支：單一 PERK，CTDA 同上＋「`HasPerk(該階 M1)`」（階內主線至少 1 點）。
   - 引擎側效果（樣式 C）由 `main_entries`（4 個主線鍵）與 `branch_entries`（28 個分支鍵）用 `(tree_id, route, tier[, index])` 硬寫；鍵是**格位**，不看名字，所以格位換了意思，進入點會悄悄留在錯的節點上。
   - `ESSB_P_BaseRules`（0x0050F0，常駐）另有「岩甲每層物理減傷 +1%」×5 段；v0.4 基礎岩甲是每層 +4%（上限 60%），山岳 +4→+5%，這筆要一起改。
5. FormID 公式：`node = (tree × 3 + route) × 5 + tier`；主線 `0x004000 + node × 15 + (rank − 1)`（0x004000–0x004B6C，2925 筆）；分支 `0x002000 + node × 4 + n`（0x002000–0x00230B 內，實際 300 筆）。EditorID 是 `ESSB_P_<tree>_<route>_<tier>_M<rank>` 與 `_B<n+1>`，**EditorID 裡沒有節點名字**，所以改名不動 EditorID。
6. CSF：`write_csf` 為每棵樹寫 `package/Elements Spellblade/SKSE/Plugins/CustomSkills/ESSB_<tree>.json`，節點 id `m{r}{k}`／`b{r}{k}{n}`，x 座標由 n 決定（`x + (1 if n == 0 else -n) × 0.95`），`validate_csf_layout` 要求分支離主線不超過兩欄、節點不重疊、`perk` 欄與 manifest 一致；點數用 `ESSB_Pts_<tree>`。
7. `plan_coverage.py` 的 `NODES` 以 v0.3 的 495 個節點為鍵，`write_plan_coverage` 要求每個節點都有登記，缺一個就 SystemExit。
8. `check_node_calls` 掃 `SCRIPTS` 裡的 `Rank`／`Br` 字面呼叫，檢查 `Br` 的 n 小於該階分支數——**這條規則假設格號連續**。

### 3.2 Papyrus 在哪裡讀點數

- 入口：`ESSBTrees.GetMainRank`（對 15 階鏈做 4 次 `HasPerk` 的二分搜尋）與 `HasBranch`，FormID 由 `MAIN_BASE`（16384＝0x4000）／`BRANCH_BASE`（8192＝0x2000）加公式算，`Game.GetFormFromFile` 取回；`RefreshTree` 把 15 格主線階數與分支位元（迴圈 `BRANCH_SLOTS = 4`）快取起來，推到 `ESSBController.RankCacheA/B`、`BranchCacheA/B`；機制程式一律透過 `ESSBController.Rank/Br` 或 `ESSBNodes.Rank/Br` 讀，**全部以 (樹, 路線, 階, n) 位置讀，不看名字**。無元素樹路線 0／1 在開形態時讀成 0（Controller 規則，DLL 照抄）。
- 字面呼叫：`src/*.psc` 裡大約 400 處（字面呼叫 398 處） `Rank(…)`／`Br(…)`（`ESSBElem/2/3`、`ESSBNoForm`、`ESSBNodes`、`ESSBController`、`ESSBGuard`、`ESSBStatus` 等），每格的所在檔案與次數已寫在第 2 節表內。
- 共用骨架（變數 `tree`，11 棵元素樹一起受影響）：`ESSBElem.OpenMult`（1,4）、`EndMult`（2,0）、`BurstMult`（2,1／2,3）、`SignatureMult`（2,4）、`MarkDurationBonus`（1,2）、`OnFormOpened`（1,3）、`OpenStrikeMult`（**分支 (1,1,0)＝開印那一擊 ×1.5**）、約 617 行的 `SetEndBoost`（2,2）、`ESSBController.NativeNodeSum`（0,1／0,3）與 `DifferencePossible`（1,1 主線、1,1 分支 0）。v0.4 把十份「開印 ×1.5」全部換成各元素專屬開場，所以 `OpenStrikeMult` 與 `DifferencePossible` 那一段要整段拿掉，各元素 (1,1,0) 的新行為要各自寫。
- **直接改 perk 進入點數值的地方（最危險）**：
  - `ESSBController.RefreshRecovery`（約 3211–3222 行）：`GetBranch(1,0,3,0)` 冰盾、`GetBranch(2,0,3,0)` 電盾、`GetBranch(8,0,3,0)` 水鏡、`GetBranch(6,0,1,1)` 聖盾（5 個進入點）→ `SetNthEntryValue`。這四格在 v0.4 分別是 REMOVED／REMOVED／REMOVED／CHANGED。
  - `ESSBNodes.RefreshWeaponPercent`：`GetMainPerk(11,0,0,rank)` 純武藝、`(11,0,3,rank)` 戰意（5 個進入點）、`(11,2,3,rank)` 淬火，15 階逐一 `SetNthEntryValue`。這三條主線在 v0.4 全部 CHANGED。
  - 如果 ESP 那邊先把進入點拿掉、這兩個函式沒跟著改，就是寫到不存在的進入點；反過來 ESP 沒改、腳本改了，舊的武器傷害／減傷效果會繼續生效。兩邊要同一輪改。
- 其他跟分支綁在一起的腳本狀態：`ESSBGuard` 的 `IceShield`、`WaterMirror`、`GuardWind` 等鏡射全域變數屬性，`ESSBController` 的 `AntiMagicAbility`（抗咒，REMOVED）、`WarmBloodAbility`（溫血）、`InductionAbility`（感應）。移除節點時這些屬性**先保留、不刪**（刪了會改變成員簽章，見 3.6）。

### 3.3 DLL 在哪裡讀點數（round 20 工作樹，N2 正在接）

- `native/include/EngineFacts.h` 的 `PerkNodes`：同一條 FormID 公式、同樣 4 次探測的二分搜尋、同樣的無元素路線 0／1 抑制；每次命中內快取。
- `native/src/Plugin.cpp` 的 `ResolvePerks`：從 manifest 讀 `perks.main_base / branch_base / main_max_rank / branch_slots`，跟編進 DLL 的 `kMainPerkBase = 0x4000`、`kBranchPerkBase = 0x2000`、`kMainMaxRank = 15`、`kBranchSlots = 4` 不一致就拒絕啟用；195 × 15 條主線每一階都要解析得到，分支格缺了就當沒有（null）。所以**配置常數一動，DLL、`ESSBTrees` 常數、`fix19_native.py` 三處要一起動**。
- `native/include/ManifestData.h` 的 `namespace node`：由 `build/fix19_native.py` 產生，每個常數都用 `NODE_IDENTITY` 核對該格的節點名稱（分支）或主線文字片段，對不上建置就失敗——這是好的絆線，重建時一定會被它擋下來，要同步改：
  - `kBloodOverflow {5,0,1,1}` 核對「血盾」→ v0.4「血溢」。
  - `kNoFormSeize {11,1,0,0}` 核對「蝕魔」→「奪魔」。
  - `kNoFormDevour {11,1,4,1}` 核對「逆流」→「噬命」（格號要保持 1，v0.4 表序是第 1 個）。
  - `kWaterSoakSlow {8,1,0}` 核對「浸濕減速」→ v0.4 這格是「開印時回復生命與耐力」，DLL 讀這格的 `SoakSlowPct` 要拿掉或改讀別處。
  - `kNoFormSilence {11,1,2}`、`kNoFormBurnCasters {11,1,3}` 的文字片段在 v0.4 改了措辭（「沉默 +0.2 秒／點」、「燒魔」），片段比對可能失敗。
  - `kProcAdept[elem]`（各元素 0,1）、`kProcMaster[elem]`（0,3）、通用樹四條與 `kCommonEcho*`、`kEarth*`、`kWindTailwind`、`kBloodLeechRatio/Reverse/Rage`、`kDivineExorcism`、`kWaterClearStream`、`kNoFormLowMagicka`、`kNoFormDepletion`、`kNoFormStillness`：格位在 v0.4 不變（枯竭機制換了，見表）。
- `HitMath.h` 有 28 處 `node::` 讀取；`kBurnMultiple = 1.0f` 旁的註解寫著「+7%／點那條主線還不存在」——v0.4 的 `noform 1 1`（燒魔倍數）、`noform 1 0`（滅法倍率）、`noform 0 0`（吸魔量）三條 DLL N2 主線，目前格子裡還是 v0.3 的 perk（`noform 0 0` 身上還掛著 0x23 武器傷害進入點），N2 不能拿它們的點數直接當新意思用，否則會跟舊進入點雙重生效。
- v0.4 標「DLL N2」的節點共 48 列（第 2 節可依「v0.4 負責」欄篩）；其中 CHANGED／NEW 而 N2 現在做不了的是：`noform 0 0 主線`、`noform 1 0 主線`、`noform 1 1 主線`、`noform 1 2 枯竭`（機制換了）、`noform 0 1 反擊`（N2 那半）、`noform 2 1 寂滅`（NEW）。其他 42 列格位與效果都不變或只是改名，N2 可以照現在的格讀。

### 3.4 FormID 穩定機制（重新編號時要過的關）

- 配置：`build_v03.ALLOCATION` 表＋上面的公式，全部確定性計算；每次建置寫出 `build/v03-formids.json`。
- 核對（全部在 `build_v03.main()` 與它呼叫的驗證裡）：
  - `build/fix-round-baseline.json`、`.codex/pre-fix2-snapshot/v03-formids.json`：每個舊 EditorID 的 `id / formid / type` 必須完全相同（`state_schema.stable_identity`，只有兩個 QUST 允許換代）。**刪掉任何一個舊 perk 記錄、或讓它換 FormID，建置就失敗。**
  - `validate_fix3`（pre-fix3 快照）：新增的記錄除了白名單外，FormID 必須落在特效段 `0x003000` 之後（`'FX not appended'`）。
  - `validate_fix4`（pre-fix4）與 `validate_mcm`（pre-fix5）：新增的 EditorID 集合必須**剛好等於**列舉的白名單；`validate_mcm` 另要求新增記錄的 ID 都大於快照裡的最大 ID（只准往後加）。
  - `state_schema.verify`（pre-fix9）：同樣是「變動的只能是兩個 QUST、新增的只能是白名單」。
  - `build/fix19_native.py` 的 `NODE_IDENTITY`，以及 `build/fix20_fixture.py` 依公式列出 N2 讀的 perk FormID。
- 結論：**新節點放在 0x002000 段的空格（附錄 A）一定會撞到 `validate_fix3` 與 `validate_mcm` 的「只准往後加」規則**，要在那幾個驗證裡加一個明確的 v0.4 樹節點白名單（像 `GUARD_WINDOW_EDIDS`、`hit19.NEW_EDIDS` 那樣），不能放寬成「什麼都可以」。已移除的節點**不能刪記錄**，要留著當「退役 perk」（不進 CSF、不能買、沒有進入點）。
- 格號就是 FormID，而 CSF 版面、`check_node_calls` 都假設格號 = 顯示順序且連續。照附錄 A 不重用的方案，有 43 階最後的格號不連續（例如黑暗 持續‧熟練 用 n = 2、3；星 持續‧新手 只剩 n = 1），所以 `plan-tree-nodes.json` 的每個分支要多存一個 `slot`（FormID 格）跟顯示順序分開，`csf_config` 的 x 改用顯示順序算，`check_node_calls` 改成檢查「n 屬於這一階的有效格」。

### 3.5 MCM 與技能樹介面依賴

- 技能樹介面是 CSF（Custom Skills Framework 3.x），13 個 `ESSB_<tree>.json` 全由建置產生；`ESSBTrees` 用 `CustomSkills.OpenCustomSkillMenu(SkillId)` 開，`SkillIds`／`TreeNames` 在 `InitTables` 寫死 13 棵。CSF 每買一個節點扣 1 點，分支 5 點由 `ESSBTrees.Reconcile` 補扣 4 點，這套不看節點內容，不用改。
- 節點名稱與說明全來自 PERK 的 `FULL`／`DESC`（樹 id、路線名在 CSF 的 `description` 裡：「規劃 5.x　路線：…」），路線改名（無元素三條、神聖「審判→聖佑」、星「星落→共鳴」）會自動帶過去；描述裡的「規劃 5.x」章節號 v0.4 沿用 v0.3，不用改。
- MCM（MCM Helper，`write_mcm`）跟個別節點無關，只有：洗點（`ESSBMCM.RespecCurrent`／`RespecAll` → `ESSBTrees.Respec`）、「節點倍率」滑桿 `ESSB_NodeScale`（範圍與 v0.4 不一致，見第 1 節）。`AllowTreeEditing` 隱藏開關不受影響。
- 設定能力（`ESSBSettingsEffect`）→ `ESSBTrees.BeginSettings/FinishSettings` 選樹開選單，不看節點。

### 3.6 會迫使 `state_schema_version` 升版的事

`state_schema` 鎖的是 `SCRIPTS` 裡每支有實例的腳本的**成員宣告**（屬性、成員變數、`AutoReadOnly` 常數）＋三個 MCM 基底類別，不看函式內容，也不看 ESP 記錄。現在 `settings.json` 是 9、鎖檔 `state-schema.lock.json` 也是 9（history 1～8）。會觸發升版的：

- 改 `ESSBTrees` 的 `BRANCH_SLOTS`、`MAIN_MAX_RANK`、`MAIN_BASE`、`BRANCH_BASE`、`TREE_COUNT` 等 `AutoReadOnly` 常數（也就是動配置）。
- 為新節點在 `ESSBController`／`ESSBGuard`／`ESSBTrees` 加屬性（例如新的常駐能力 Spell、新的鏡射 GlobalVariable、冰鎧／聖佑用的新效果）或加成員變數（新的冷卻計時、共鳴層暫存…）。
- 刪掉移除節點用的屬性（`AntiMagicAbility`、`IceShield`、`WaterMirror`…）或成員。
- 為了「舊存檔一次性退點」加一個腳本成員旗標。

不會觸發的：只改 perk 記錄、只改函式內容、新增 GLOB／MGEF／SPEL 記錄但用 `Game.GetFormFromFile` 在執行期取（跟現在取 perk 的方式一樣）。升版本身是允許的（exactly +1，舊 quest 留 stub），但它會讓玩家的腳本狀態換到新 quest；如果這一輪同時要升，**跟 N2／N3 協調成一次**，不要每個切片各升一次。

## 4. 建議的工作拆分

前提：等 round 20（N2）收尾、指揮 commit 之後再開工，因為下面第 3、6 步會碰 `fix19_native.py`、`ManifestData.h`、`build_v03.py` 同一批檔案。

1. **決定三件政策（要使用者點頭）**：(a) 已移除的分支格不重用（本檔推薦）還是重用；(b) 23 條換機制的主線與 49 個換機制的分支，舊存檔已投的點怎麼辦——推薦在載入時「偵測到舊版版面就把受影響的樹整棵退點」，版本記在新的 GLOB（執行期 `GetFormFromFile` 取，不加屬性，就不用升 schema）；(c) 設計文件第 1 節列的四處不一致怎麼解。
2. **新解析器**：新增 `plan_trees_v04.py`（或讓 `plan_trees.py` 支援兩種版本），讀 v0.4 的 5 欄表；輸出每個分支帶 `slot`（沿用 v0.3 名字配對的格、改名對照表、新節點用附錄 A 的格）與顯示順序、`trigger`、`owner`；保留 v0.3 的 `main_original` 欄位作歷史。把改名對照表與「已退役 perk」清單寫成資料，不要散在程式裡。
3. **ESP 產生器**：`build_esp` 改用新 plan；退役 perk 照樣產生記錄（同 EditorID／FormID，`playable=0`、不進 CSF、無進入點、DESC 註明退役）；重寫 `main_entries`／`branch_entries` 的鍵表（刪掉 v0.4 不存在的減傷／武器傷害進入點，加上 v0.4 標「引擎效果（PERK）」的：法盾分擔、水盾、止水、聖盾（改讀聖佑）、聖佑新手主線、不移、定神、御風、空中追擊、疾電…），改 `ESSB_P_BaseRules` 岩甲每層 4%；在 `validate_fix3`／`validate_fix4`／`validate_mcm`／`state_schema.verify` 加 v0.4 樹節點白名單；`csf_config` 改用顯示順序排 x；`check_node_calls` 改檢查有效格；`apply_balance_text`／`apply_fix8_decisions` 改成 v0.4 的縮放表（v0.4 已標明哪些「不吃節點倍率」）。
4. **Papyrus 同步**（跟第 3 步同一輪）：`ESSBController.RefreshRecovery` 與 `ESSBNodes.RefreshWeaponPercent` 先處理（見 3.2）；拿掉共用的「開印 ×1.5」；修 `ESSBElem` 的 (tree,2,2) 共用 bug；逐樹把 CHANGED／REMOVED 的 `Rank`／`Br` 讀取改掉或刪掉；Papyrus 負責的 NEW 節點（例如 餘壓、星殘、連斷類形態開關）照各列「負責」欄接。屬性一律先保留。
5. **`plan_coverage.py` 重建**：以 v0.4 節點為鍵重做 `NODES`，每列寫「負責切片」；DLL N3～N6 的節點先標 DEFERRED（理由＝對應切片未上線），不要為了數字好看標 IMPLEMENTED。
6. **DLL 同步**：`fix19_native.py` 的 `NODE_IDENTITY` 改名（血溢／奪魔／噬命）、拿掉 `kWaterSoakSlow`、補 `noform 0 0 / 1 0 / 1 1` 三條主線與「寂滅」的常數，`HitMath.h` 把 `kBurnMultiple` 等寫死值換成讀點數；跑 native 測試。
7. **舊存檔遷移**：實作第 1 步 (b) 的退點；退役 perk 在載入時若玩家持有就移除並退 5 點（純 `HasPerk` 檢查，不需要新狀態）。
8. **驗收**：`python build_v03.py` 全綠；CSF 13/13 valid；新舊 FormID 比對表（沿用格全等、退役格仍在、新格全在白名單）；一份 v0.3 存檔讀進來的實機卡（洗點前後點數正確、沒有殘留減傷）。

## 5. 風險

1. **格位就是語意**：Papyrus（字面約 400 處）、DLL（28 處）、`branch_entries`／`main_entries`、`plan_coverage` 全部用 (樹, 路線, 階, n) 讀，不看名字。任何一處沒同步，就是「點了 A 卻生效 B」，而且編譯不會報錯。只有 `fix19_native.py` 的 `NODE_IDENTITY` 會擋 DLL 那一側。
2. **舊存檔的已購節點**：23 條主線、49 個同名換機制分支，舊存檔的點數會直接變成新效果；49 個退役分支的 5 點會被卡住。沒有遷移，玩家會覺得「點數不見了」或「節點亂跳」。
3. **殘留的引擎效果**：像 `ESSB_P_common_0_2_M*`（受傷 -0.5%／點）、`ESSB_P_noform_0_0_M*`（武器傷害）、冰盾／電盾／水鏡／影甲／星體／星光／預知這些 PERK 進入點，如果 ESP 沒刪，玩家會同時有舊的減傷和 v0.4 的新機制；`SetNthEntryValue` 那兩個函式如果先刪 ESP 沒改腳本，會寫到錯的進入點。
4. **驗證規則的「只准往後加」**：新節點落在 0x002000 段的空格，會被 `validate_fix3`、`validate_mcm` 擋下；改驗證時要加明確白名單，不能整條拿掉，否則 FormID 漂移再也抓不到。
5. **格號不連續**：不重用方案下 43 階格號不連續，`check_node_calls`、CSF 版面驗證都會失敗，要先把「格」與「顯示順序」分開。
6. **跟 N2 同時改同一批檔**：`build_v03.py`、`build/fix19_native.py`、`ManifestData.h`、`ESSBController.psc` 正在被 round 20 改；兩邊並行一定衝突。另外 N2 如果先照 v0.4 意思去讀 `noform 0 0 / 1 0 / 1 1`，而樹還沒重建，會跟舊 perk 的進入點雙重生效。
7. **大量節點依賴還沒上線的切片**：v0.4 的 NEW 與 CHANGED 節點大多標 DLL N3／N4／N5（受擊、施法事件、範圍掃描、每秒點）。樹重建後這些節點會「買得到、沒效果」；要嘛在 DESC 標「尚未生效」，要嘛這些格在對應切片上線前不開放購買。
8. **schema 升版的時機**：只要加一個屬性就要升版，而升版會把玩家的腳本狀態換到新 quest；跟 N3 以後的切片若各升一次，玩家會連續遇到幾次狀態重置。建議合併。
9. **設計文件本身的不一致**（第 1 節四點）：骨架表與各樹表打架，實作者不能自己選，要先問。
10. **本盤點的限制**：分類是逐列人工判讀加文字比對，RETUNED 與 CHANGED 的界線（例如火熱度「層→階」算 RETUNED）是判斷，不是機械規則；Papyrus 次數是 regex 掃字面呼叫，用變數 `tree` 讀的只列了共用骨架那幾個函式；DLL 部分是 round 20 的未完成狀態。


## 附錄 A：新節點建議格位（「不重用已移除格」方案）

每一階的分支格是 `0x002000 + ((tree×3+route)×5+tier)×4 + n`，n = 0..3。下表只挑 v0.3 從沒用過的 n，所以不會有舊存檔「持有某個已移除節點、卻被當成新節點」的情況。47 個新節點全部放得下，沒有任何一階需要超過 4 格。

| 樹 | 路線 | 階 | 新節點 | 建議 n | 建議 EditorID | 建議 FormID |
|---|---|---|---|---|---|---|
| `fire` | 2 | 新手 | 餘壓 | 2 | `ESSB_P_fire_2_0_B3` | 0x00202A |
| `frost` | 0 | 大師 | 冰鎧 | 2 | `ESSB_P_frost_0_3_B3` | 0x00204A |
| `frost` | 0 | 大師 | 凍傷 | 3 | `ESSB_P_frost_0_3_B4` | 0x00204B |
| `frost` | 1 | 大師 | 霜爆 | 2 | `ESSB_P_frost_1_3_B3` | 0x00205E |
| `lightning` | 0 | 大師 | 逆電 | 2 | `ESSB_P_lightning_0_3_B3` | 0x002086 |
| `lightning` | 1 | 大師 | 雷鳴 | 3 | `ESSB_P_lightning_1_3_B4` | 0x00209B |
| `earth` | 2 | 專精 | 蓄能 | 1 | `ESSB_P_earth_2_2_B2` | 0x0020E5 |
| `blood` | 0 | 新手 | 血刃 | 2 | `ESSB_P_blood_0_0_B3` | 0x00212E |
| `divine` | 0 | 大師 | 破邪斬 | 2 | `ESSB_P_divine_0_3_B3` | 0x002176 |
| `divine` | 1 | 熟練 | 誓約 | 2 | `ESSB_P_divine_1_1_B3` | 0x002182 |
| `divine` | 2 | 大師 | 天誅 | 2 | `ESSB_P_divine_2_3_B3` | 0x00219E |
| `water` | 0 | 熟練 | 水盾 | 2 | `ESSB_P_water_0_1_B3` | 0x0021E6 |
| `water` | 0 | 大師 | 潮身 | 2 | `ESSB_P_water_0_3_B3` | 0x0021EE |
| `water` | 0 | 傳奇 | 止水 | 1 | `ESSB_P_water_0_4_B2` | 0x0021F1 |
| `water` | 1 | 大師 | 淨潮 | 2 | `ESSB_P_water_1_3_B3` | 0x002202 |
| `water` | 2 | 熟練 | 退潮 | 2 | `ESSB_P_water_2_1_B3` | 0x00220E |
| `darkness` | 0 | 新手 | 咒延 | 1 | `ESSB_P_darkness_0_0_B2` | 0x00221D |
| `darkness` | 0 | 熟練 | 懼咒 | 2 | `ESSB_P_darkness_0_1_B3` | 0x002222 |
| `darkness` | 0 | 熟練 | 怨縛 | 3 | `ESSB_P_darkness_0_1_B4` | 0x002223 |
| `darkness` | 0 | 專精 | 狂咒 | 1 | `ESSB_P_darkness_0_2_B2` | 0x002225 |
| `darkness` | 0 | 大師 | 狂宴 | 2 | `ESSB_P_darkness_0_3_B3` | 0x00222A |
| `darkness` | 0 | 大師 | 回魘 | 3 | `ESSB_P_darkness_0_3_B4` | 0x00222B |
| `darkness` | 0 | 傳奇 | 亡衛 | 1 | `ESSB_P_darkness_0_4_B2` | 0x00222D |
| `darkness` | 1 | 熟練 | 狂刃 | 2 | `ESSB_P_darkness_1_1_B3` | 0x002236 |
| `darkness` | 2 | 新手 | 殘魂 | 2 | `ESSB_P_darkness_2_0_B3` | 0x002246 |
| `darkness` | 2 | 熟練 | 冥印 | 2 | `ESSB_P_darkness_2_1_B3` | 0x00224A |
| `darkness` | 2 | 專精 | 噬咒 | 2 | `ESSB_P_darkness_2_2_B3` | 0x00224E |
| `darkness` | 2 | 大師 | 冥召 | 2 | `ESSB_P_darkness_2_3_B3` | 0x002252 |
| `astral` | 0 | 新手 | 星鏈 | 1 | `ESSB_P_astral_0_0_B2` | 0x002259 |
| `astral` | 0 | 熟練 | 聚星 | 2 | `ESSB_P_astral_0_1_B3` | 0x00225E |
| `astral` | 0 | 大師 | 餘輝 | 2 | `ESSB_P_astral_0_3_B3` | 0x002266 |
| `astral` | 0 | 傳奇 | 星蝕 | 1 | `ESSB_P_astral_0_4_B2` | 0x002269 |
| `astral` | 0 | 傳奇 | 天穹 | 2 | `ESSB_P_astral_0_4_B3` | 0x00226A |
| `astral` | 1 | 大師 | 星門 | 2 | `ESSB_P_astral_1_3_B3` | 0x00227A |
| `astral` | 2 | 專精 | 星殘 | 1 | `ESSB_P_astral_2_2_B2` | 0x002289 |
| `astral` | 2 | 大師 | 墜星 | 2 | `ESSB_P_astral_2_3_B3` | 0x00228E |
| `noform` | 0 | 新手 | 逼近 | 1 | `ESSB_P_noform_0_0_B2` | 0x002295 |
| `noform` | 0 | 熟練 | 蓄流 | 2 | `ESSB_P_noform_0_1_B3` | 0x00229A |
| `noform` | 0 | 專精 | 化勁 | 1 | `ESSB_P_noform_0_2_B2` | 0x00229D |
| `noform` | 0 | 大師 | 餘魔 | 2 | `ESSB_P_noform_0_3_B3` | 0x0022A2 |
| `noform` | 0 | 傳奇 | 破式 | 1 | `ESSB_P_noform_0_4_B2` | 0x0022A5 |
| `noform` | 0 | 傳奇 | 無魔 | 2 | `ESSB_P_noform_0_4_B3` | 0x0022A6 |
| `noform` | 1 | 大師 | 咒返 | 2 | `ESSB_P_noform_1_3_B3` | 0x0022B6 |
| `noform` | 2 | 熟練 | 寂滅 | 2 | `ESSB_P_noform_2_1_B3` | 0x0022C2 |
| `noform` | 2 | 傳奇 | 萬寂 | 1 | `ESSB_P_noform_2_4_B2` | 0x0022CD |
| `common` | 1 | 新手 | 跳印 | 1 | `ESSB_P_common_1_0_B2` | 0x0022E5 |
| `common` | 1 | 大師 | 印潮 | 2 | `ESSB_P_common_1_3_B3` | 0x0022F2 |

## 附錄 B：沿用 FormID、但 v0.4 表格順序不同的分支

照 v0.4 表格由上往下編號的話，下面這幾個會換到別的格（FormID 改變、舊存檔失去已買的節點）。建議保持 v0.3 的格號，顯示順序另外存。

- `ESSB_P_frost_0_3_B2`（寒反）：v0.3 第 2 格，v0.4 表序第 3 格
- `ESSB_P_astral_2_1_B2`（星斷）：v0.3 第 2 格，v0.4 表序第 1 格
- `ESSB_P_noform_0_1_B1`（反擊）：v0.3 第 1 格，v0.4 表序第 2 格
- `ESSB_P_noform_0_3_B2`（不屈）：v0.3 第 2 格，v0.4 表序第 1 格
- `ESSB_P_noform_1_1_B3`（反咒）：v0.3 第 3 格，v0.4 表序第 2 格
- `ESSB_P_noform_1_4_B2`（逆流）：v0.3 第 2 格，v0.4 表序第 1 格
- `ESSB_P_noform_1_4_B3`（封印）：v0.3 第 3 格，v0.4 表序第 2 格
