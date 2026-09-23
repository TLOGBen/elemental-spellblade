# 觸發分類：每個機制由什麼觸發、新架構由誰負責

- 撰寫：2026-09-23 21:40（+08:00）。純分析文件，不改任何設計或程式。
- 設計真相：`元素魔戰士規劃-v0.3_alter.md`（以下稱 alter）。架構：`design-latency-2026-09-20.md` 4.11 與第 6 節（DLL 切片 N1～N6）。還原項：`design-compromises-2026-09-22.md`。
- 「現在由誰跑」讀的是 `src/*.psc` 與 `native/src/Plugin.cpp`＋`native/include/*.h`（N1）目前的內容。現況程式大多仍是 round 18 的 v0.3 實作（狀態容器 `ESSBStatus`、8 格登記表），跟 alter 有多處不同，列在第 5 節。

## 1. 分類與縮寫

**觸發類別**

| 類別 | 意思 |
|---|---|
| 命中當下 | 玩家武器命中的那一幀（`TESHitEvent`），含重擊、潛行、弓弩旗標 |
| 狀態開始 | 目標或玩家身上某個效果剛掛上（開印就是「印記開始」） |
| 狀態每秒 | 效果存在期間每秒發生的事（DoT、披風、冰封減速、領域） |
| 結束-過期 | 效果時間到自然消失（印記過期終焉、引信到期、階梯退階） |
| 結束-被切 | 換元素後的第一擊，新印記驅散舊印記（被切終焉、有接管元素） |
| 結束-融斷 | 按 Z 關閉形態，範圍內印記一次結清 |
| 目標死亡 | 目標死時看屍體身上有什麼 |
| 你被打 | 玩家受到命中（受擊 sink） |
| 自身計時 | 玩家側的每秒維持、冷卻、視窗到期（不綁在某個目標效果上） |
| 開關形態 | 開形態、切換、關形態（不含融斷的結算本身） |
| 自身門檻〔新增〕 | 玩家生命跌破某比例（冰心、庇護、自動洩壓）；可以由「你被打」或「每秒輪詢」偵測，本身就是兩可 |
| 被動 | 條件成立就一直生效的加減值（PERK 進入點、能力），沒有離散的觸發瞬間 |
| 其他 | 上面都不是（目標施法、環境切換、內部冷卻） |

「狀態結束（切／融／期）」表示三種結束方式都會觸發（alter 2.6：三種都算終焉）。

**新架構負責者**

| 縮寫 | 意思 | 切片 |
|---|---|---|
| DLL命中 | `TESHitEvent` sink 內決定並套用 | N1 已做附傷；N2 強度；N3 目標狀態；N4 自身資源 |
| DLL受擊 | 同一 sink 處理「目標＝玩家」的命中 | N4 |
| DLL事件〔新增〕 | 效果移除事件（過期、引信、退階，待查證）、死亡事件、融斷的範圍掃描 | N3（過期／退階）、N5（融斷、死亡、範圍） |
| DLL每秒 | DLL 的每秒執行點（**未驗證**；compromises 把放血歸 N5，latency 第 6 節把每秒計時歸 N6 且說留 Papyrus，兩份文件不一致） | N5／N6 |
| 引擎 | 效果自己運作：時長、每秒值、披風、PERK 條件 | —（由套用者寫進強度／時長） |
| Papyrus | 介面、低頻、Papyrus 專用 API（推力、恐懼、復生、CSF、神佑延遲死亡、每秒維持費） | — |

**狀態存放**：「效果強度」＝ magnitude（層數、計數、每秒值）；「時長」＝ duration／剩餘秒數；「GLOB」＝全域變數（開關、鏡射給 PERK 條件）；「perk」＝投點。DLL 什麼都不存。

**現況縮寫**：`Ctl.`＝ESSBController、`Elem.`／`Elem2.`／`Elem3.`＝ESSBElem*、`React.`＝ESSBReactions、`Guard.`＝ESSBGuard、`Status.`＝ESSBStatus、`NoForm.`、`Nodes.`、`Rules.`＝ESSBFormRules、`DLL(N1)`＝Plugin.cpp 的附傷 sink。

**骨架節點只寫一次**：各元素共用的主線（附傷 +1%、同調每段附傷、開印後 5 秒、印記持續、X 臨、開印效果、終焉、融斷 ×2、接管附傷、終焉招式 +3%）與「開印那一擊 ×1.5」「開印時附近 1 人也 X」兩類分支，寫在第 2.2 節的骨架表，各元素表不再重複。

---

## 2. 分表

### 2.1 無元素（5.1、2.8）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 無形態基準真傷 5×G，重擊 ×1.5 | 命中當下 | `Ctl.ApplyNoFormBaseline`（DLL N1 只管有形態時） | DLL命中 | GLOB（樹等級、MCM 倍率） | N2 |
| 純武藝新手：無形態武器傷害 +1%／點 | 被動 | 引擎 perk（`Nodes.RefreshWeaponPercent` 寫倍率） | 引擎 | perk、GLOB FormActive | — |
| 穩步：格擋耐力 −20% | 被動 | 引擎 perk | 引擎 | perk | — |
| 重擊碎甲 1%／點 5 秒（破勢 8 秒） | 命中當下 | `NoForm.OnMartialHit` | DLL命中 | 目標效果時長、perk | N2 |
| 反擊：格擋成功後 3 秒下一擊 +30% | 你被打 → 命中當下 | `Guard.OnHitEx`（SetRiposte）＋`Ctl.OnNoFormHit` | DLL受擊（掛視窗）＋引擎（0x23 讀視窗） | 自身視窗效果時長 | N4 |
| 疾攻：連續命中每次重擊耗耐 −10%（最多 −50%） | 命中當下 | `Ctl.OnNoFormHit`（ComboHits、GLOB Combo） | DLL命中（連段數）＋引擎（PERK 讀 GLOB） | 連段效果強度＋時長 4 秒、GLOB ESSB_Combo | N4 |
| 暴擊率 +1%／點（自有判定） | 命中當下 | `NoForm.OnMartialHit` | DLL命中 | perk | N2 |
| 節奏：4 秒內命中 3 次 → 回耐＋戰意 +1 | 命中當下 | `Ctl.OnNoFormHit`→`NoForm.OnCombo` | DLL命中 | 連段效果強度／時長 | N4 |
| 戰意 0～5 | 命中當下（節奏給） | `Ctl.AddResolve`（腳本變數＋GLOB） | DLL命中 | 自身效果強度、GLOB ESSB_Resolve | N4 |
| 戰意 5 秒未命中歸零 | 結束-過期 | `Ctl.Tick`（每秒比時間） | 引擎（效果時長） | 時長 | N4 |
| 戰意每層武器傷害 +0.5%／點 | 被動 | 引擎 perk 讀 GLOB | 引擎 | GLOB、perk | N4（鏡射） |
| 不屈：戰意 ≥3 受傷 −10% | 被動 | 引擎 perk 讀 GLOB | 引擎 | GLOB | — |
| 終結：戰意滿層重擊 +等量真傷 3%／點 | 命中當下 | `NoForm.OnMartialHit` | DLL命中 | 戰意效果強度、perk | N4 |
| 處決：戰意滿、重擊、目標 <25% → ×3，消耗戰意 | 命中當下 | `NoForm.OnMartialHit` | DLL命中 | 戰意效果強度 | N4 |
| 破魔：削魔、回魔、削減量 ×0.5 真傷、破魔印 8 秒 | 命中當下 | `NoForm.OnManaBreak` | DLL命中 | 破魔印時長、perk | N2 |
| 蝕魔（固定值與 10% 最大魔力取高）、真傷比例 +3%／點、大師主線削魔 +5%／點、枯竭、靜寂 | 命中當下 | `NoForm.OnManaBreak` | DLL命中 | perk、目標魔力（引擎值） | N2 |
| 斷咒：打斷施法中的敵人，每 5 秒一次 | 命中當下 | `NoForm.OnManaBreak`（IsCasting＋`Ctl.OnAnimationEvent` 記錄） | DLL命中 | 目標 5 秒冷卻效果 | N2 |
| 沉默：魔力削到 0 → 沉默 1～4 秒（封印：3 公尺） | 命中當下 | `NoForm.ApplySilence` | DLL命中（封印要掃描） | 目標效果時長 | N2（封印 N5） |
| 反噬：受法術傷害回魔 | 你被打 | `Guard.OnHitEx` | DLL受擊 | perk | N4 |
| 反咒：帶破魔印的敵人施法 → 受施法消耗 100% 真傷 | 其他（目標施法） | `ESSBCounter`／`Ctl.OnAnimationEvent`→`NoForm.OnCounterSpell` | Papyrus（**沒有切片涵蓋目標施法事件**，見 3.2） | 破魔印（目標效果） | — |
| 破護：不受元素披風反傷（第一跳仍吃到） | 你被打 | `Guard.OnHitEx`（SetCloakGuard） | DLL受擊 | 自身視窗效果 | N4 |
| 抗咒：無形態魔抗 +15% | 開關形態 | `Ctl.RefreshAbilities` | Papyrus（能力） | perk | — |
| 目標魔力 <25% 命中 +3%／點 | 命中當下 | `Ctl.ApplyTrueDamage`／`NoForm.TrueMult` | DLL命中 | perk | N2 |
| 逆流：真傷 50% 轉生命 | 命中當下 | `Ctl.ApplyTrueDamage` | DLL命中 | perk | N2 |
| 無魔：擊殺施法者回滿耐力魔力 | 目標死亡 | `NoForm.OnKill` | DLL事件 | — | N5 |
| 融斷 +2%／+3%、範圍 +0.3 公尺／點、收束 20 公尺 | 結束-融斷 | `Ctl.OnFormClosed`／`NoForm.BurstMult`、`BurstRadius` | DLL事件（掃描） | perk | N5 |
| 免門檻：融斷後下一次開形態不需魔力 | 結束-融斷 → 開關形態 | `NoForm.OnBurst`→`Ctl.SetFreeOpen` | Papyrus（開形態門檻在 `ESSBInput`） | 自身標記效果或 GLOB | — |
| 餘燼：關形態後 10 秒（延續 20 秒）無形態命中附前元素附傷 +2%／點 | 結束-融斷 → 命中當下 | `NoForm.OnBurst`＋`Ctl.OnNoFormHit` | DLL命中 | 視窗效果時長、GLOB 前一元素 | N2 |
| 連斷：融斷後 5 秒內重開保留一半同調 | 開關形態 | `NoForm.OnBurst` | Papyrus（開形態）→ DLL 原生函式重套同調 | 視窗效果強度＝保留的同調數 | N4 |
| 淬火：融斷後 10 秒武器傷害 +1%／點 | 結束-融斷 | `NoForm.OnBurst` | 引擎（視窗效果＋0x23） | 時長 | N5 |
| 斷界：融斷後施加所有被結清元素的弱化 3 秒 | 結束-融斷 | `NoForm.OnBurstTarget` | DLL事件 | 目標效果時長 | N5 |
| 回流：融斷回魔，每印記 B_max ×0.5 | 結束-融斷 | `NoForm.OnBurst` | DLL事件 | — | N5 |
| 雙斷：融斷後 3 秒內按 Z 開形態 → 範圍開印 | 開關形態 | `Ctl.OnFormOpened` | Papyrus → DLL 原生函式（範圍開印） | 視窗效果時長 | N5 |

### 2.2 通用（共通系統 2.x、5.2，與各元素骨架）

**共通系統**

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 附傷（形態開啟，武器 0～7、9） | 命中當下 | DLL(N1) 套法術＋`Ctl.ApplyProc` 差額補丁 | DLL命中 | GLOB（元素、形態）、perk | N1 ✔／N2 |
| 每擊隨機 B（區間擲骰） | 命中當下 | DLL(N1) 用法術固定值（平均）；差額用平均 | DLL命中 | — | N2 |
| 重擊 ×1.5、潛行射擊視為重擊 | 命中當下 | DLL(N1) 用 `IsPowerAttacking`／`IsSneaking` 條件；Papyrus 用 HitData 旗標 | DLL命中（HitData 65536／2048） | — | N2 |
| 目標資格（非同伴、非受命、活著、非格擋；已交戰 30 秒） | 命中當下 | DLL(N1) 過濾；`Ctl.MarkEngaged` | DLL命中（已交戰嵌在附傷法術） | 目標「已交戰」效果時長 | N1／N3 |
| 印記：開印版／刷新版，8 秒（浸濕 10 秒） | 命中當下 | `Ctl.OnValidHit`→`InstallMark`／`ApplyMark`（8 格登記表） | DLL命中 | 目標印記效果時長 | N3 |
| 開印反應 | 狀態開始 | `Ctl.OpenMark`→`React.Open` | DLL命中（判定）＋Papyrus `ESSBReactions`（本體，ModEvent，到 N5） | 目標效果 | N3→N5 |
| 終焉：被切 | 結束-被切 | `Ctl.InstallMark`→`EndMark(reason 0)` | DLL命中（先舊終焉再新開印） | 目標效果 | N3 |
| 終焉：過期 ×1 | 結束-過期 | `Ctl.Tick` 每秒比 `RegUntil`→`EndMark(2)` | DLL事件（效果移除，待查證；否則 `ESSBMark`＋餘燼 Papyrus） | 印記時長 | N3 |
| 融斷：15 公尺內印記一次結清 × K_sync | 結束-融斷 | `Ctl.OnFormClosed` | Papyrus（Z）→ DLL事件（掃描結算） | 同調效果強度、印記 | N5 |
| 開印／終焉每目標 1 秒內部冷卻、反應不遞迴 | 其他 | `Ctl`（登記表內） | 引擎（目標 1 秒冷卻效果）＋DLL 判斷 | 目標冷卻效果 | N3 |
| 範圍效果上限 5 人、目標資格過濾 | 其他 | `Ctl.ScanTargets` | DLL事件（掃描） | — | N5 |
| 印記沒有 8 目標上限 | 其他 | **現況仍是 8 格登記表**（`Ctl.AcquireSlot`） | 不需要（引擎持有） | — | N3 |
| 同調 +1／有效命中 | 命中當下 | `Ctl.AddSync`（GLOB ESSB_Sync） | DLL命中 | 同調效果強度、GLOB SyncStage 鏡射 | N4 |
| 同調升段（5／15／30） | 命中當下 | `Ctl.ComputeSyncStage`／`OnSyncStage`（音效、ModEvent） | DLL命中（套段效果）＋Papyrus（音效，可選） | 段效果、GLOB | N4 |
| 同調切換／關閉歸零 | 開關形態 | `Ctl.OnFormSwitched`／`OnFormClosed` | Papyrus → DLL 原生函式清除 | 同調效果 | N4 |
| 武器光三檔亮度 | 被動（讀 SyncStage） | 引擎（形態能力條件讀 GLOB） | 引擎 | GLOB | — |
| 切換：先寫 GLOB，再換能力 | 開關形態 | `ESSBInput`→`Ctl.SwitchForm` | Papyrus | GLOB | — |
| 開形態魔力門檻 10% | 開關形態 | `ESSBInput` | Papyrus | — | — |
| 維持費（每秒扣魔） | 自身計時 | `Rules.OnUpdate` | Papyrus | 樹等級、GLOB | （N6 選配） |
| 魔力歸零 2 秒自動關閉 | 自身計時 | `Rules.OnUpdate` | Papyrus | — | — |
| 經驗（命中、開印、終焉、融斷） | 命中當下等 | `Trees.OnValidHitXP` 等 | DLL 送 ModEvent → Papyrus（CSF API） | — | N3～N5 |
| 環境偵測（雨雪、水中、夜晚） | 自身計時（5 秒） | `Ctl.EnvCheck` | Papyrus | GLOB EnvWet／EnvStormy／EnvNight | — |
| 環境效果：雨雪視為浸濕、夜晚暗 +20%／星範圍 ×1.5、白天聖 +20% | 命中當下（讀 GLOB） | `Ctl.GetHitMult` 等 | DLL命中 | GLOB | N2 |
| 死亡機制：帶神聖印記→化灰、帶黑暗印記→亡者歸來、化灰優先 | 目標死亡 | `Ctl.OnKillEvent`（**用擊殺歸屬 `KillElementFor`**） | DLL事件（判定）＋Papyrus（崩解特效、復生 AI） | 印記（No Death Dispel） | N5 |
| 切換提示文字、切換音效 | 開關形態 | `Ctl.SwitchForm` | Papyrus | MCM GLOB | — |
| 領域（火域等 11 種）同時最多 3 個 | 結束-融斷 → 狀態每秒 | `Ctl.StartDomain`／`TickDomain`（控制器每秒） | Papyrus 每秒，或 Hazard | — | N6 選配 |

**5.2 通用樹**

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 同調門檻 −2%／點 | 命中當下（算門檻） | `Nodes.SyncThresholdScale` | DLL命中 | perk | N4 |
| 承接：切換保留 1/3 同調 | 開關形態 | `Nodes.CarryOverSync` | Papyrus → DLL 原生函式 | 同調效果強度 | N4 |
| 同調二段附傷 +1%、三段重擊附傷 +2% | 命中當下 | `Ctl.GetHitMult` | DLL命中 | perk、GLOB | N2 |
| 不移：被打斷或擊倒不失去同調 | 你被打 | 無 | **不明**：alter 沒有「被打斷會失去同調」的基礎規則（見 3.2） | — | — |
| 專一：同形態 60 秒後門檻再減半 | 自身計時 | `Ctl.FormHeldSeconds` | 引擎（開形態掛 60 秒效果，到期換「專一」標記）＋DLL 讀 | 效果時長 | N4 |
| 同調三段受傷 −0.5%／點、定神（免疫自有減速） | 被動 | 引擎 perk／`Nodes.SelfSlowImmune` | 引擎 | GLOB、perk | — |
| 極致：同調三段每 10 擊額外全額附傷 | 命中當下 | `Ctl.OnWeaponHit`（ExtremeCount 變數） | DLL命中 | 計數效果強度 | N4 |
| 回饋：升段時回血回魔 B_max ×2 | 命中當下（升段） | `Nodes.OnSyncStage` | DLL命中 | — | N4 |
| 化身：同調三段每 30 秒觸發當前元素的持續傳奇效果 | 自身計時 | `Ctl.Tick`→`Elem*.OnAvatar` | Papyrus 計時（或 30 秒冷卻效果到期→DLL事件） | 冷卻效果時長 | N6／N3 |
| 永續：Z 關閉時同調三段 → 保留一段到下一次開形態 | 結束-融斷 → 開關形態 | `Ctl.OnFormClosed` | Papyrus → DLL 原生函式 | 自身標記效果 | N4 |
| 附傷 +1%／點（開啟新手、大師） | 命中當下 | `Ctl.GetHitMult` | DLL命中 | perk | N2 |
| 印記持續 +0.2 秒／點 | 命中當下 | `Nodes.MarkDurationBonus`→`Ctl.ApplyMark` | DLL命中 | perk | N3 |
| 順轉：開形態免門檻、切換後 1 秒受傷 −50% | 開關形態 | `Ctl.SwitchForm`（SetGuardSwitch） | Papyrus（視窗效果）＋引擎 perk | 視窗時長 | — |
| 先制 +2 同調、專精主線 +1 同調／每 5 點（開印時） | 狀態開始 | `Nodes.OpenSyncBonus` | DLL命中 | 同調效果強度 | N4 |
| 雙印：第三個元素到來時切掉較舊的 | 命中當下 | `Ctl.InstallMark`（RegSeq 比序） | DLL命中（讀兩印記已過時間） | 印記時長 | N3 |
| 深印：開印那一擊 ×1.5 | 命中當下 | `Nodes.OpenStrikeMult`→`Ctl.ApplyProc` | DLL命中 | — | N3 |
| 廣印：開印擴散到附近 1 人 | 狀態開始 | `Ctl.AfterOpen` | DLL命中＋掃描 | — | N3／N5 |
| 臨界：開形態附近敵人減速 30% 2 秒 | 開關形態 | `Nodes.OnFormOpened` | Papyrus → DLL 原生函式（掃描） | 目標效果 | N5 |
| 狀態上限 +1 層／每 5 點；萬象：層數效果 +25% | 命中當下（寫強度時） | `Ctl.StackCap`、`Status.Cap`、`Nodes.OmniMult` | DLL命中 | perk | N3／N4 |
| 終焉 +1%／點 ×2 | 狀態結束（切／融／期） | `Nodes.CommonEndMult` | 隨終焉處理者 | perk | N3／N5 |
| 融斷 +1%、+2%／點 | 結束-融斷 | `React.End` | DLL事件 | perk | N5 |
| 餘響＋關閉專精主線：切換後首次命中附前元素 50%（+3%／點） | 開關形態 → 命中當下 | `Ctl.OnFormSwitched`＋`OnWeaponHit`（SwitchHitPending） | DLL命中 | 切換視窗效果、GLOB 前一元素 | N2 |
| 反哺：每次終焉回 B_max 魔力 | 狀態結束（切／融／期） | `Nodes.OnEndReward` | 隨終焉處理者 | — | N3／N5 |
| 疊印：終焉後舊印記保留 4 秒為副印記，融斷再結算 | 結束-被切 | `Ctl.KeepAsSecond` | DLL命中 | 副印記效果時長 | N3 |
| 連鎖終焉：附近帶同印記者也終焉 ×0.5 | 狀態結束（切／融／期） | `React.ChainEnd` | DLL事件（掃描） | — | N5 |
| 三重奏：10 秒內三種不同元素終焉 → 第三次 ×3、下一次融斷保留同調 | 狀態結束（切／融／期） | `Nodes.TrioMult`／`Ctl.PushTrio` | DLL（每元素一顆 10 秒自身標記） | 自身標記效果時長 | N3／N5 |
| 協奏：切換後首次終焉 ×1.5 | 開關形態 → 結束-被切 | `Ctl.TakeSwitchEnd` | DLL命中 | 切換視窗效果 | N3 |
| 安全閥：融斷時受傷 −50% 2 秒 | 結束-融斷 | `Ctl.OnFormClosed` | 引擎（視窗效果＋perk） | 時長 | N5 |
| 大協奏：切換後首次終焉讓範圍內舊印記者各終焉 | 結束-被切 | `Ctl.TakeGrandConcert`→`React.ChainEnd` | DLL命中＋掃描 | 切換視窗效果 | N5 |
| 雙生：雙持左手另附前一形態元素 30 秒 | 命中當下（左手） | `Ctl.OnWeaponHit`（TwinElement） | DLL命中（來源武器判左手） | 視窗效果時長、GLOB 前一元素 | N2 |

**各元素骨架（5.3～5.13 共用，只寫一次）**

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 持續熟練：X 附傷 +1%／點 | 命中當下 | `Ctl.GetHitMult` | DLL命中 | perk | N2 |
| 持續大師：同調每段 X 附傷 +1%／點 | 命中當下 | `Ctl.GetHitMult` | DLL命中 | perk、GLOB SyncStage | N2 |
| 開啟熟練：開印後 5 秒內 X 附傷 +1%／點 | 狀態開始 → 命中當下 | `Ctl.SetOpenBoost`／`GetHitMult` | DLL命中（開印時掛 5 秒視窗，之後讀） | 自身視窗效果時長 | N3 |
| 開啟專精：X 印記持續 +0.2 秒／點 | 命中當下 | `Elem.MarkDurationBonus` | DLL命中 | perk | N3 |
| 開啟大師：X 臨（開形態時範圍內各開印一次，2 公尺 +0.2／點；星 +1／點） | 開關形態 | `Ctl.OnFormOpened`→`Elem*.OnFormOpened` | Papyrus → DLL 原生函式（掃描＋開印） | — | N5 |
| 開啟傳奇：開印效果 +3%／點 | 狀態開始 | `Elem.OpenMult`（`React.Open`） | 隨開印處理者 | perk | N3 |
| 關閉新手：終焉 +2%／點 | 狀態結束（切／融／期） | `Elem.EndMult` | 隨終焉處理者 | perk | N3／N5 |
| 關閉熟練、大師：X 印記的融斷 +2%／點 | 結束-融斷 | `Elem.BurstMult` | DLL事件 | perk | N5 |
| 關閉專精（冰雷聖毒水）：終焉後 5 秒內接管元素附傷 +1%／點 | 結束-被切 → 命中當下 | `Elem.OnEnd`→`Ctl.SetEndBoost` | DLL命中 | 自身視窗效果時長 | N3 |
| 關閉傳奇：終焉招式 +3%／點（爆燃、碎冰、放電、地震、落地、血潮、裁決、催毒、導引、死咒、星落） | 狀態結束（切／融／期） | `Elem.SignatureMult` | 隨終焉處理者 | perk | N3／N5 |
| 開啟熟練分支「開印那一擊 ×1.5」（烈火點燃、深霜結、強感電、深裂痕、深血痕、慈光、濃毒、深濕、明星；風與暗無此分支） | 命中當下 | `Elem.OpenStrikeMult`→`Ctl.ApplyProc` | DLL命中 | — | N3 |
| 開啟新手分支「開印時附近 1 人也 X」（寒潮 +2 凍結、傳導、震波、風襲、血濺 1 層、聖輝、毒濺 2 劑、廣佈、暗染、星散） | 狀態開始 | `Elem*.OpenX`（`Ctl.ScanTargets`） | DLL命中＋掃描 | 鄰居身上的效果 | N3／N5 |

### 2.3 火（1.1、2.6、2.7、5.3）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 熱度升階（微熱→灼熱→白熱；成熟 2 秒） | 命中當下 | **現況是目標熱度 0～10**（`Ctl.HitStacks`→`AddStack` kind 1） | DLL命中 | 自身階效果＋成熟計時效果 | N3 |
| 微熱、灼熱 6 秒未命中退一階 | 結束-過期 | `Status.Tick`（目標熱度 6 秒歸零） | 引擎（階時長）＋DLL事件（到期套低一階；否則 `ESSBTierDecay`） | 階時長 | N3 |
| 火附傷 +15／35／60／90% 依熱度 | 命中當下 | `Elem.FireHitMult`（過熱 +50%） | DLL命中（或 0x1D 讀自身階） | 自身階效果 | N2／N3 |
| 點燃（開印）：熱度升一階＋B_max ×0.5 | 狀態開始 | `React.Open`（目標熱度 +2） | DLL命中＋反應 | 自身階 | N3 |
| 進入白熱：8 秒引信、命中不刷新、全身火焰著色 | 命中當下 | 無 | DLL命中（套白熱階） | 白熱效果時長 | N3 |
| 白熱火源：3 公尺敵人每秒火傷並掛火印記 | 狀態每秒 | 無 | 引擎（披風） | 披風關聯法術強度（**誰在何時寫**待定，見 3.2） | N3 |
| 火源掛的火印記不觸發開印 | 其他 | 無 | 引擎（專用印記版本） | — | N3 |
| 火源代價：每秒最大生命 0.5%（留 1 點） | 自身計時 | 無 | Papyrus 每秒（與維持費同 tick） | 白熱效果存在 | — |
| 自動洩壓：生命 <10% | 自身門檻 | 無 | 兩可（見 3.1） | — | N4／— |
| 過熱：白熱引信到期 → 付 10%、15 公尺內帶火印記者爆燃、熱度歸零 | 結束-過期 | **現況是同調三段後的過熱計數**（`Ctl.AddSelf` kind 4） | DLL事件（引信到期＋掃描） | 白熱時長 | N3／N5 |
| 洩壓：白熱中切換或融斷 → 安全、不付代價 | 開關形態 | 無 | Papyrus → DLL 原生函式驅散白熱（要標明「主動驅散」，不算過熱） | — | N3 |
| 爆燃（終焉）：B_max × 熱度倍率 × (1＋消耗加成) | 狀態結束（切／融／期） | `React.EndFire`→`Elem.Detonate`（讀目標熱度） | DLL（被切：命中；過期：事件；融斷：掃描） | 自身階、目標其他元素效果 | N3／N5 |
| 爆燃消耗：階 +25%×階、裂痕／浸濕／失衡 +25%、血痕與中毒剩餘 50% 轉即時、星痕立即引爆 | 狀態結束（切／融／期） | 無 | 同上（讀目標效果、驅散） | 目標效果強度×剩餘秒 | N3 |
| 火源倍率 N +0.2／點（持續新手主線）、業火 +0.1／點 | 被動（寫披風強度時） | 無 | 由寫披風強度者讀 perk | perk | N3 |
| 添薪：引信 8 → 12 秒 | 命中當下（套白熱時） | 無（現況「上限 15」） | DLL命中 | perk | N3 |
| 烙印：重擊升兩階 | 命中當下 | `Elem.HitStacks`（重擊熱度 +4） | DLL命中 | — | N3 |
| 溫血：火形態耐力回復 +20% | 開關形態 | `Ctl.RefreshAbilities` | Papyrus（能力） | perk | — |
| 帶火印記目標火抗 −1%／點 | 命中當下 | `Elem.ApplyFireResistShred`（帶熱度目標） | DLL命中（或印記效果帶條件減抗） | 目標效果 | N3 |
| 熔心：洩壓與過熱後保留微熱 | 開關形態／結束-過期 | `Elem.IgniteResidual`（保留一半目標熱度） | DLL（洩壓與過熱處理內） | 自身階 | N3 |
| 熔身：過熱改為 10 秒熔身（附傷 +100%、受傷 −20%、每秒回耐 5） | 結束-過期 → 狀態每秒 | `Ctl.AddSelf`→`SetMolten`＋`TickTimers` | DLL事件（套熔身）＋引擎（10 秒、回耐） | 熔身效果時長 | N3 |
| 灼身：被近戰命中 → 攻擊者掛火印記＋火傷，每 3 秒 | 你被打 | `Guard.OnHitEx`（攻擊者熱度 +1） | DLL受擊 | 攻擊者 3 秒冷卻效果 | N4 |
| 火浴：白熱期間火源每燒到一人回血 B_max ×0.1／秒 | 狀態每秒 | `Elem.OnIgnite`（自燃回血，舊語意） | 兩可（見 3.1） | — | ？ |
| 浴火：同調三段帶火印記目標對你傷害 −30% | 被動 | 引擎 perk | 引擎（0x24 類目標分頁） | GLOB | — |
| 熔爐：白熱到期改升第四階「熔燒」再 6 秒 | 結束-過期 | 無（現況「過熱上限 20」） | DLL事件 | 熔燒時長 | N3 |
| 開啟新手主線：開印後 5 秒內升階免等待 +0.5 秒／每 5 點 | 狀態開始 | `Elem.OpenStacks`（舊：開印熱度 +1） | DLL命中（視窗） | 視窗時長 | N3 |
| 引火：開印升兩階 | 狀態開始 | `Elem.OpenStacks`（舊：熱度 +5） | DLL命中 | — | N3 |
| 餘熱：開印回 15 耐力 | 狀態開始 | `Elem.OpenFire` | DLL命中 | — | N3 |
| 焰起強化：「焰起」額外對範圍敵人一次火附傷 | 狀態開始 | `Elem.OpenFire` | DLL命中＋掃描 | — | N5 |
| 烈火之始：開印目標生命 >80% → 熱度直接白熱 | 狀態開始 | `Elem.OpenFire`（舊：目標熱度 8） | DLL命中 | — | N3 |
| 火種：微熱灼熱不因未命中退階 | 結束-過期（抑制） | `Status.Tick`（`Elem.HasTinder`） | DLL命中（套階時給長時長） | perk | N3 |
| 先燃：同調三段開印立即 ×0.5 爆燃 | 狀態開始 | `Elem.OpenFire` | DLL命中 | — | N3 |
| 猛爆：爆燃不消耗目標狀態 | 狀態結束（切／融／期） | `Elem.Detonate`（不清熱度） | 隨爆燃處理者 | perk | N3 |
| 洩壓（分支）：白熱中切換／融斷後保留灼熱，火源多留 2 秒 | 開關形態 | `Elem.VentMult`（舊：過熱轉額外爆燃） | Papyrus → DLL 原生函式 | 披風時長 | N3 |
| 熾焰：白熱以上爆燃 ×1.5 | 狀態結束（切／融／期） | `Elem.Detonate`（舊：熱度 ≥8） | 隨爆燃處理者 | 自身階 | N3 |
| 熔斷：融斷後熱度保留 | 結束-融斷 | `Elem.KeepHeatOnBurst`（舊：目標熱度保留） | DLL事件 | 自身階 | N5 |
| 關閉專精主線：消耗加成 +1%／點 × 被消耗數 | 狀態結束（切／融／期） | `Elem.DetonatePerLayer`（舊：每層倍率） | 隨爆燃處理者 | perk | N3 |
| 餘燼（火）：火終焉後接管元素開印 ×1.5 | 結束-被切 | `Elem.EndFireNodes`→`Status.SetNextOpenMult` | DLL命中（同一擊內） | — | N3 |
| 焚天：火終焉時範圍內帶火印記者一起爆燃 | 狀態結束（切／融／期） | `Elem.EndFireNodes`（帶熱度） | DLL＋掃描 | — | N5 |
| 火葬：爆燃擊殺者對附近再爆 ×0.5 | 目標死亡 | `Elem.OnCremation`（傷害前預測） | DLL事件（死時讀「爆燃致死」標記） | 目標 1 秒標記 | N5 |
| 火域：火印記融斷後 5 秒火域（火傷 +20%、熱度免等待、白熱引信暫停） | 結束-融斷 → 狀態每秒 | `Ctl.StartDomain`／`TickDomain`（舊：熱度累積 ×2） | Papyrus 每秒或 Hazard；「引信暫停」兩可（見 3.1） | 領域、目標標記 | N6 |

### 2.4 冰（2.3、2.6、5.4）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 凍結量表：命中 +1、重擊 +2、暴風雪 ×2 | 命中當下 | `Ctl.HitStacks`→`AddStack` kind 2（`ESSBStatus`） | DLL命中 | 目標階效果（凍結 1～5） | N3 |
| 6 秒未命中歸零 | 結束-過期 | `Status.Tick` | 引擎（階時長 6 秒） | 時長 | N3 |
| 冰封（量表 5），3 秒 | 命中當下 | `Status`（Freeze≥5）＋`SyncFrozenFx` | DLL命中（套第 5 階） | 第 5 階時長 3 秒 | N3 |
| 冰封期間強減速 50%（絕對零度再 −2%／點） | 狀態每秒 | `Elem.OnFrozenTick`（`Status.Tick` 每秒重套） | 引擎（冰封階自帶減速；強度由套用者寫） | 階效果強度 | N3 |
| 冰封 3 秒後量表歸零 | 結束-過期 | `Status.Tick` | 引擎 | — | N3 |
| 碎冰：冰封中第一擊 20% 最大生命真傷（首領 10%），冰封結束 | 命中當下 | **無**（現況碎冰只在終焉，且是處決門檻版） | DLL命中 | 第 5 階存在 | N3 |
| 霜結（開印）：凍結 +3、減速 25% 3 秒 | 狀態開始 | `React.Open` | DLL命中 | 目標效果 | N3 |
| 碎冰（終焉）：冰封→20% 真傷＋碎甲 10% 5 秒；未冰封→B_max ×1 | 狀態結束（切／融／期） | `React.EndFrost`→`Elem.Shatter`（處決 <20%、×2.5） | DLL（被切命中；過期事件；融斷掃描） | 目標階 | N3／N5 |
| 持續新手主線：凍結累積 +5%／點（小數以機率取整） | 命中當下 | `Elem.HitStacks`（RoundStochastic） | DLL命中 | perk | N3 |
| 寒蝕：重擊凍結 +2 | 命中當下 | `Elem.HitStacks` | DLL命中 | — | N3（語意與基礎重疊，見 3.2） |
| 深寒：冰封中耐力不回復、攻擊 −20% | 狀態每秒 | `Elem.OnFrozenTick` | 引擎（冰封階帶 perk 條件的附加效果） | — | N3 |
| 霜膚：冰形態受傷 −5% | 被動 | 引擎 perk | 引擎 | GLOB | — |
| 冰封目標冰附傷 +2%／點 | 命中當下 | `Ctl.GetHitMult` | DLL命中（或 0x1D） | 目標階 | N3 |
| 永凍：冰封 +2 秒，結束後保留一半 | 結束-過期 | `Status.Tick`（`Elem.FrozenResidual`） | DLL事件（到期套第 2～3 階；否則 `ESSBTierDecay`） | 階時長 | N3 |
| 連鎖冰封：冰封目標死亡 → 附近凍結 +3、減速 | 目標死亡 | `Elem.OnKill` | DLL事件＋掃描 | 屍體上的階 | N5 |
| 冰盾：每命中 +1（最多 5）、8 秒 | 命中當下 | **無每擊 +1**（只有冰甲開印 +1，`Elem.OpenFrost`） | DLL命中 | 自身效果強度、GLOB ESSB_IceShield | N4 |
| 冰盾：被打 −1 並抵 30% | 你被打 | `Guard.OnHitEx`→`Ctl.ConsumeIceShield`；減傷在 perk | DLL受擊＋引擎 perk | 同上 | N4 |
| 寒反：攻擊你的敵人被減速 | 你被打 | `Guard.OnHitEx` | DLL受擊 | 攻擊者效果 | N4 |
| 冰心：生命 <30% 自動冰封附近「帶寒意」敵人，30 秒一次 | 自身門檻 | `Elem.OnTick`（控制器每秒） | 兩可（見 3.1）；「寒意」已不存在（見 3.2） | 30 秒冷卻效果 | N4／— |
| 開啟新手主線：開印凍結 +1／每 3 點 | 狀態開始 | `Elem.OpenStacks` | DLL命中 | perk | N3 |
| 冰甲：開印得 1 層冰盾 | 狀態開始 | `Elem.OpenFrost` | DLL命中 | 自身效果強度 | N4 |
| 冰臨強化：冰臨附帶減速 30% 3 秒 | 開關形態 | `Elem.OnFormOpened` | Papyrus → DLL 原生函式 | — | N5 |
| 霜鎖：開印目標 3 秒移速 −30% | 狀態開始 | `Elem.OpenFrost` | DLL命中 | 目標效果時長 | N3 |
| 冰晶：開印時你受傷 −10% 3 秒 | 狀態開始 | `Elem.OpenFrost`（GLOB GuardIce） | DLL命中（自身視窗）＋引擎 perk | 視窗時長 | N3 |
| 絕霜：同調三段開印直接冰封 | 狀態開始 | `Elem.OpenFrost` | DLL命中 | — | N3 |
| 銳碎：碎冰 25%（首領 12%） | 命中當下／狀態結束 | `Elem.ShatterThreshold`（舊：處決門檻 30%） | 隨碎冰處理者 | perk | N3 |
| 冰崩：碎冰改 3 公尺，命中所有冰封目標 | 狀態結束（切／融／期） | `Elem.EndFrostNodes` | DLL＋掃描（是否也適用命中碎冰不明，見 3.2） | — | N5 |
| 冰封融斷：冰印記融斷時冰封視同碎冰 | 結束-融斷 | `Elem.FrostBurstShatter` | DLL事件 | — | N5 |
| 寒留：冰終焉後接管元素印記 +4 秒 | 結束-被切 | `Elem.EndFrostNodes`→`Ctl.NextMarkBonus` | DLL命中（同一擊） | — | N3 |
| 冰河：冰終焉時目標冰封 → 範圍內冰封者一起碎冰 | 狀態結束（切／融／期） | `Elem.EndFrostNodes` | DLL＋掃描 | — | N5 |
| 碎甲加深：10% → 20% | 狀態結束 | `Elem.Shatter` | 隨碎冰處理者 | perk | N3 |
| 冰棺：碎冰後再冰封 2 秒（第二次碎冰 ×0.5） | 命中當下／狀態結束 | `Elem.Shatter`→`SetFrozen(2)`（沒有 ×0.5） | DLL | 「冰棺」冰封效果（與一般冰封分開才能 ×0.5） | N3 |
| 冰原：融斷後 5 秒冰原（減速 50%、凍結累積 ×2、你免疫減速） | 結束-融斷 → 狀態每秒 | `Ctl.StartDomain`／`TickDomain` | Papyrus 每秒或 Hazard（每秒給目標「在冰原」標記，DLL 命中時讀） | 目標標記 | N6 |

### 2.5 雷（2.1、2.6、5.5）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 附傷 1～25 擲 N 次取最大，N＝1＋電荷 | 命中當下 | DLL(N1) 五檔、N=1；`Ctl.ApplyProc` 差額以 13 計 | DLL命中 | 電荷效果強度 | N2（N 在 N4） |
| 附傷削目標魔力 50% | 命中當下 | 引擎（附傷法術第 2 效果）；差額另寫 | 引擎＋DLL 強度覆寫（多效果覆寫待查證） | — | N2 |
| 電荷：開印 +2、命中 +1，上限 6／10／13 | 命中當下 | `Ctl.AddSelf` kind 1（腳本變數＋GLOB） | DLL命中 | 自身效果強度、GLOB ESSB_Charge | N4 |
| 電荷 10 秒未命中歸零 | 結束-過期 | **`Ctl.Tick` 每秒 −1（v0.3）** | 引擎（效果時長 10 秒） | 時長 | N4 |
| 電荷三檔視覺、滿格音效 | 命中當下 | 無 | DLL命中 | — | N4 |
| 感電（開印）：你 +2 電荷、目標魔力 −B_max | 狀態開始 | `React.Open` | DLL命中 | — | N3 |
| 放電（終焉）：電荷×30% B_max、削魔 50%、跳 2 人 40%、滿格 ×2、吃重擊倍率 | 狀態結束（切／融／期） | `React.EndShock`→`Elem.DischargeAll`／`Discharge`（讀 LastHitWasPower） | DLL（被切命中；過期事件；融斷掃描） | 電荷效果強度 | N3／N5 |
| 雷雨：每 3 秒 +1 電荷 | 自身計時 | `Ctl.Tick` | 兩可（見 3.1） | GLOB EnvStormy | ？ |
| 持續新手主線：放電每格 +1%／點 | 狀態結束 | `Elem.Discharge` | 隨放電處理者 | perk | N3 |
| 感應：雷形態魔力回復 +20% | 開關形態 | `Ctl.RefreshAbilities` | Papyrus（能力） | perk | — |
| 電弧：放電跳附近 2 人 40% | 狀態結束 | `Elem.Discharge`（現況把比例提到 80%） | 隨放電處理者 | perk | N3（與基礎重疊，見 3.2） |
| 靜電：被近戰命中 → 攻擊者感電 | 你被打 | `Guard.OnHitEx`（另 +1 電荷、削魔） | DLL受擊 | — | N4 |
| 電荷上限 +1／每 3 點 | 命中當下 | `Elem.ChargeCap` | DLL命中 | perk | N4 |
| 雷暴：電荷滿時普攻 30% 放電 | 命中當下 | `Ctl.OnWeaponHit`→`Elem.StormChance` | DLL命中 | 電荷效果強度 | N4 |
| 電盾：電荷 ≥5 受傷 −15% | 被動 | 引擎 perk 讀 GLOB | 引擎 | GLOB ESSB_Charge | N4（鏡射） |
| 疾電：放電後 3 秒受傷 −15% | 狀態結束 → 自身計時 | `Elem.Discharge`→`SetShockRecent` | 引擎（視窗效果）由放電處理者掛 | 視窗時長 | N3 |
| 天雷：同調三段放電改對範圍內所有感電目標 | 狀態結束（切／融／期） | `Elem.DischargeAll` | DLL＋掃描 | — | N5 |
| 雷神：同調三段電荷滿層自動放電並回魔 | 兩可 | `Elem.OnTick`（每秒；對 `NearestMarked`） | 兩可（見 3.1） | 電荷效果強度 | N4 |
| 開啟新手主線：開印電荷 +1／每 5 點 | 狀態開始 | `Elem.OpenStacks` | DLL命中 | perk | N4 |
| 充能開印：開印回 B_max 魔力 | 狀態開始 | `Elem.OpenShock` | DLL命中 | — | N3 |
| 雷臨強化：雷臨時立即 5 電荷 | 開關形態 | `Elem.OnFormOpened` | Papyrus → DLL 原生函式 | 電荷效果強度 | N4 |
| 感電削弱：感電目標魔抗 −10% | 被動（印記存在） | `Elem.OpenShock` | 引擎（雷印記帶 perk 條件的減抗） | 印記 | N3 |
| 雷閃：開印後 2 秒移速 +15% | 狀態開始 | `Elem.OpenShock` | DLL命中（自身視窗） | 時長 | N3 |
| 電蝕：削魔 100%，目標魔力 0 時雷附傷 +25% | 命中當下 | `Elem.ShockHitMult` | DLL命中（或 0x1D） | perk | N2 |
| 先雷：同調三段開印立即放電、不耗電荷 | 狀態開始 | `Elem.OpenShock` | DLL命中 | — | N3 |
| 連鎖：跳躍 2 → 5 人 | 狀態結束 | `Elem.Discharge` | 隨放電處理者 | perk | N3 |
| 蓄餘：雷終焉不消耗電荷 | 狀態結束（切／融／期） | `Elem.Discharge`（abConsume） | 隨放電處理者 | perk | N3 |
| 雷斷：雷印記融斷附全部電荷放電加成 | 結束-融斷 | `Elem.ShockBurstBonus` | DLL事件 | 電荷效果強度 | N5 |
| 餘電：雷終焉後接管元素開印附 ×0.5 放電 | 結束-被切 | `Ctl.AfterOpen` | DLL命中（同一擊） | — | N3 |
| 雷殛：雷終焉對範圍內所有感電目標各一次全額放電 | 狀態結束（切／融／期） | `Elem.EndShockNodes` | DLL＋掃描 | — | N5 |
| 過載終焉：終焉時電荷 ≥8 ×2 | 狀態結束（切／融／期） | `Elem.OverloadMult`（只對雷終焉） | 隨終焉處理者 | 電荷效果強度 | N3（範圍不明，見 3.2） |
| 雷霆：雷印記融斷後 5 秒每次命中放電 ×0.3 | 結束-融斷 → 命中當下 | `Ctl.OnWeaponHit`（ThunderLeft） | DLL命中（讀視窗） | 自身視窗時長 | N4 |

### 2.6 地（2.6、5.6）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 岩甲：開印 +2、命中 +1，上限 5／10／13，護甲 ＝ 層 ×15 | 命中當下 | `Ctl.AddSelf` kind 2→`SyncRockArmor`（能力強度） | DLL命中 | 自身效果強度、GLOB ESSB_RockArmor | N4 |
| 岩甲：被打 −1（山岳免除） | 你被打 | `Guard.OnHitEx`→`Ctl.ConsumeRockArmor` | DLL受擊 | 同上 | N4 |
| 岩甲：不衰減、離開形態清空 | 開關形態 | `Ctl.ClearSelfAll` | Papyrus → DLL 原生函式清除 | — | N4 |
| 裂痕（開印）：護甲 −30、耐力 −10、你回 10 耐＋2 岩甲 | 狀態開始 | `React.Open` | DLL命中 | 目標效果時長 8 秒 | N3 |
| 裂痕 8 秒、命中刷新 | 命中當下 | `Status`（Fissure） | DLL命中 | 時長 | N3 |
| 地震（終焉）：3 公尺 B_max ×1.5、削耐 B_max ×2、耐力 0 跌倒（8 秒一次）、其餘減速 | 狀態結束（切／融／期） | `React.EndEarth`→`Elem2.Quake`；跌倒 `Ctl.Knockdown` | DLL（掃描）＋Papyrus（推力） | 目標 8 秒推力冷卻效果 | N3／N5 |
| 裂痕護甲削減 +2／點 | 狀態開始 | `Elem2.FissureArmor` | DLL命中 | perk | N3 |
| 磐石：岩甲每層 +25 | 命中當下 | `Elem2.RockArmorPerLayer` | DLL命中（寫強度） | perk | N4 |
| 震擊：重擊消耗「滿層」裂痕，1.5× 爆傷＋削耐 50 | 命中當下 | `Elem2.OnEarthHit` | DLL命中 | 目標裂痕 | N3（裂痕是單層，「滿層」不明，見 3.2） |
| 厚土：上限 10 | 命中當下 | `Elem2.RockCap` | DLL命中 | perk | N4 |
| 命中削耐 +0.5／點、汲力（一半轉你） | 命中當下 | `Elem2.OnEarthHit` | DLL命中 | perk | N2 |
| 不動：岩甲 ≥5 免疫擊退 | 被動 | 引擎 perk 讀 GLOB | 引擎 | GLOB | N4（鏡射） |
| 反震：岩甲滿層被近戰命中 → 反震土傷＋攻擊者跌倒，10 秒一次，清空岩甲 | 你被打 | `Guard.OnHitEx`→`Elem2.OnEarthRetaliate` | DLL受擊＋Papyrus（推力） | 自身 10 秒冷卻效果 | N4 |
| 地動：同調三段重擊對耐力 <30% 目標跌倒（5%／點） | 命中當下 | `Elem2.OnEarthHit` | DLL命中＋Papyrus（推力） | 目標推力冷卻 | N4 |
| 山岳：同調三段岩甲不因被打減少、每層物理減傷 +3% | 你被打／被動 | `Guard.OnHitEx`（條件）＋perk | DLL受擊＋引擎 | GLOB | N4 |
| 開印岩甲 +1／每 5 點；岩膚 +4 | 狀態開始 | `Elem2.OpenStacks` | DLL命中 | perk | N4 |
| 地臨強化：岩甲滿層＋範圍減速 | 開關形態 | `Elem2.OnFormOpened` | Papyrus → DLL 原生函式 | 自身效果強度 | N4／N5 |
| 地基：開印目標 3 秒移速 −30% | 狀態開始 | `Elem2.OpenEarth` | DLL命中 | 目標效果時長 | N3 |
| 裂地：開印在腳下留 3 秒減速地帶 | 狀態開始 → 狀態每秒 | `Elem2.OpenEarth` | DLL命中（套地帶）＋Papyrus 或 Hazard | — | N3／N6 |
| 先震：同調三段開印立即 ×0.5 地震（不跌倒） | 狀態開始 | `Elem2.OpenEarth` | DLL命中＋掃描 | — | N5 |
| 崩裂 ×2.0、廣震 5 公尺、地震削耐 +3%／點 | 狀態結束 | `Elem2.QuakeK`／`QuakeRadius`／`QuakeStamina` | 隨地震處理者 | perk | N5 |
| 固土：土終焉後岩甲滿層 | 狀態結束（切／融／期） | `Elem2.EndEarthNodes` | 隨終焉處理者 | 自身效果強度 | N4 |
| 地斷：融斷附 3 秒泥沼 | 結束-融斷 → 狀態每秒 | `Elem2.EndEarthNodes`→`Ctl.StartDomain` | Papyrus 每秒或 Hazard | — | N6 |
| 山崩：土終焉對範圍內帶裂痕者各一次地震 | 狀態結束（切／融／期） | `Elem2.EndEarthNodes` | DLL＋掃描 | — | N5 |
| 塵暴：地震使範圍敵人攻擊 −20% 3 秒 | 狀態結束 | `Elem2.QuakeOne` | 隨地震處理者 | 目標效果 | N5 |
| 地裂：融斷後 5 秒地裂帶（減速 50%、耐力不回復） | 結束-融斷 → 狀態每秒 | `Ctl.TickDomain` | Papyrus 每秒或 Hazard | — | N6 |

### 2.7 風（1.1、2.6、5.7）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 風形態：移速 +10%、衝刺耗耐 −20% | 開關形態 | `Ctl.RefreshWindAbilities` | Papyrus（能力） | perk | — |
| 潛行：不減速、腳步減半（無聲：完全無聲、潛行移速 +20%） | 其他（潛行狀態變化） | `Ctl.Tick` 每秒讀 IsSneaking→`RefreshWindStealth` | 引擎（條件式能力，晚 ≤1 秒）或 Papyrus 每秒 | — | — |
| 潛行攻擊：風附傷 ×3（暗風 ×5）、風勢直接滿 | 命中當下 | DLL(N1) 用 IsSneaking 選法術；`Ctl.ApplyProc`、`ElementHitHook` | DLL命中（HitData 2048） | — | N2／N4 |
| 風勢：開印 +2、命中 +1，門檻 4（亂舞 3） | 命中當下 | `Ctl.AddSelf` kind 3 | DLL命中 | 自身效果強度、GLOB ESSB_Wind | N4 |
| 風勢到門檻送風刃並歸零 | 命中當下 | `Elem2.CheckWindGauge` | DLL命中 | 同上 | N4 |
| 風勢 5 秒未命中歸零 | 結束-過期 | `Ctl.Tick` | 引擎（時長） | 時長 | N4 |
| 失衡 3 秒（失衡中風刃 +30%） | 狀態開始 | `Status`（Unbalance） | 引擎（效果＋0x1D） | 目標效果時長 | N3 |
| 風痕（開印）：風勢 +2、拉近 1.5 公尺（3 秒一次）、失衡 | 狀態開始 | `React.Open`＋`Elem2.OpenWind`→`Ctl.PullIn` | DLL命中＋Papyrus（推力） | 目標推力冷卻 | N3 |
| 吹飛（終焉）：目標＋附近 2 人風刃、吹飛 3 公尺（8 秒一次）、首領改減速 | 狀態結束（切／融／期） | `React.EndWind`→`Elem2.WindBlade`／`BlowAway` | DLL＋掃描＋Papyrus（推力） | 推力冷卻 | N3／N5 |
| 多段觸發：被切時接管元素的命中效果 ×N（基礎 2，傷害第 2 次起 ×0.5） | 結束-被切 | **無** | DLL命中（同一擊內迴圈 N 次） | perk | N4 |
| 融斷吹上天：浮空 2 秒、落地 B_max ×0.5 | 結束-融斷 → 結束-過期 | `Ctl.OnFormClosed`／`LiftUp`，落地由 `Status.Tick`→`Ctl.OnLanding` | DLL事件（掃描、浮空到期）＋Papyrus（推力） | 浮空效果時長 | N5／N3 |
| 風刃傷害 +2%／點 | 命中當下 | `Elem2.WindBladeMult` | 隨風刃處理者 | perk | N4 |
| 迴旋：風刃對附近 2 人 | 命中當下 | `Elem2.WindBlade` | DLL命中＋掃描 | — | N5 |
| 順風：命中回耐 5 | 命中當下 | `Elem2.OnWindHit` | DLL命中 | — | N2 |
| 移速 +0.5%／點、疾風（移速 +10%、衝刺 −50% 後半引擎無法） | 開關形態 | `Elem2.WindSpeedBonus` | Papyrus（能力） | perk | — |
| 追風：風刃命中回耐 3 並失衡 | 命中當下 | `Elem2.WindBladeOne` | DLL命中 | — | N4 |
| 殘影：風勢滿時被近戰命中 30% → 下一擊無效，消耗風勢 | 你被打 | `Guard.OnHitEx`（SetGuardWind） | DLL受擊 | 自身視窗效果 | N4 |
| 暗風：潛行攻擊送出的風刃 ×2 | 命中當下 | `Elem2.SneakMult` | DLL命中 | perk | N4 |
| 千刃：同調三段每命中機率附風刃 | 命中當下 | `Elem2.OnWindHit` | DLL命中 | perk | N4 |
| 御風：同調三段免疫減速、失衡目標受你所有傷害 +30% | 被動 | `Elem2.WindSlowImmune`／`TargetDamageMult` | 引擎（0x23／0x1D 目標分頁） | GLOB | — |
| 開印風勢 +1／每 5 點；疾風痕：開印風勢直接滿 | 狀態開始 | `Elem2.OpenStacks` | DLL命中 | perk | N4 |
| 拉近距離 +0.1 公尺／點 | 狀態開始 | `Elem2.PullDistance` | 隨推力（Papyrus） | perk | — |
| 輕躍：開印後 3 秒移速 +10% | 狀態開始 | `Elem2.OpenWind` | DLL命中（自身視窗） | 時長 | N3 |
| 氣旋：風臨把範圍敵人拉到面前 2 公尺 | 開關形態 | `Elem2.OnFormOpened` | Papyrus（推力） | — | — |
| 奇襲：潛行攻擊的開印同時觸發終焉、不拉近 | 命中當下 | `Elem2.OpenWind` | DLL命中 | — | N3 |
| 牽引：拉近目標 2 秒減速 80%（上限 70%） | 狀態開始 | `Ctl.PullTo` | DLL命中 | 目標效果時長 | N3 |
| 氣流：開印回 10 耐 | 狀態開始 | `Elem2.OpenWind` | DLL命中 | — | N3 |
| 先風：同調三段開印附風刃 | 狀態開始 | `Elem2.OpenWind` | DLL命中 | — | N4 |
| 亂流：風刃附近目標 2 → 5 | 狀態結束 | `React.EndWind` | 隨吹飛處理者 | perk | N5 |
| 上天：吹飛改吹上天、落地 B_max ×1.0 | 狀態結束 → 結束-過期 | `Elem2.BlowAway`／`LandingDamage` | DLL＋Papyrus（推力）；落地 DLL事件 | 浮空時長 | N3／N5 |
| 風斷：風印記融斷每目標兩段風刃 | 結束-融斷 | `Elem2.EndWindNodes` | DLL事件 | — | N5 |
| 關閉專精主線：多段 N +1／每 5 點 | 結束-被切 | **`Elem2.BlowDistance`（仍是吹飛距離 +0.2 公尺）** | DLL命中 | perk | N4 |
| 風渦：終焉時 5 公尺內敵人被拉向目標 | 狀態結束（切／融／期） | `Elem2.EndWindNodes` | DLL（掃描）＋Papyrus（推力） | — | N5 |
| 颶風：融斷吹上天改對範圍內所有敵人 | 結束-融斷 | `Elem2.EndWindNodes` | DLL事件＋Papyrus | — | N5 |
| 順勢：風終焉後 5 秒接管元素命中皆附風刃 | 結束-被切 → 命中當下 | `Ctl.OnWeaponHit`（WindFollowLeft） | DLL命中（讀視窗） | 自身視窗時長 | N4 |
| 落地傷害 +5%／點 | 結束-過期（落地） | `Elem2.LandingDamage` | DLL事件 | perk | N3 |
| 空中追擊：浮空目標受所有傷害 ×1.5、風刃再推高 | 被動＋命中當下 | `Elem2.TargetDamageMult`、`WindBladeOne` | 引擎（0x23）＋DLL命中＋Papyrus（推力） | 浮空效果 | N4 |
| 連殺：帶風印記者被潛行殺死 → 5 秒不解除潛行、下一次潛行附傷 ×2 | 目標死亡 | `Ctl.OnKillEvent`／`SettleSneakKill`／`KeepSneak` | DLL事件（讀 `ESSB_LastHitSneak`）＋Papyrus（偵測 API） | 目標 1 秒標記、自身視窗 | N5 |

### 2.8 血（1.1、2.3、2.6、5.8）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 血位命中倍率（線性內插） | 命中當下 | DLL(N1) 四段法術（0.85／0.5／0.2）＋`Ctl.GetBloodHitMult` | DLL命中 | 玩家生命%（引擎值） | N2 |
| 吸血：命中流血目標，比例依血位 | 命中當下 | `Elem2.OnBloodHit`→`Ctl.Leech` | 兩可（見 3.1；指揮官建議 DLL命中） | — | N2 |
| 維持扣血（每秒，依血位，留 1 點） | 自身計時 | `Rules.OnUpdate`→`Ctl.PayBloodCost` | Papyrus | — | — |
| 重擊扣血（依血位）、重擊不耗耐 | 命中當下 | `Ctl.OnWeaponHit`→`PayBloodCost`；耗耐在 perk | DLL命中（直接扣值）＋引擎 perk | — | N4 |
| 血痕：開印 2、命中 +1，上限 8／12／15，10 秒，命中刷新全部 | 命中當下 | `Ctl.HitStacks`→`AddStack` kind 5（環狀桶，每層各自計時） | DLL命中 | 效果強度＝層×每層、時長 | N3 |
| 血痕 DoT 每秒 | 狀態每秒 | `Status.Tick`→`Ctl.ApplyDotDamage`（腳本每秒扣） | 引擎（DoT 自己跳） | 效果強度 | N3 |
| 放血：每層每秒扣目標當下生命 0.3%（首領 0.1%） | 狀態每秒 | `Status.Tick`→`Ctl.ApplyBleedDrain`（現況已是當下生命） | DLL每秒；不可行則 DLL命中換算 | 血痕強度、目標生命 | N5／N6 |
| 血痕過期 | 結束-過期 | `Status.Tick`（環狀桶老化） | 引擎 | 時長 | N3 |
| 血痕（開印）：2 層＋依血位吸血 | 狀態開始 | `React.Open` | DLL命中 | — | N3 |
| 血潮（終焉）：剩餘強度×剩餘秒×血位倍率＋目標當前生命 10%（首領 3%）；治療＝×吸血×2 | 狀態結束（切／融／期） | `React.EndBlood`（`Status.BleedRemaining`） | DLL（被切命中；過期事件；融斷掃描） | 血痕強度與剩餘秒 | N3／N5 |
| 每層 +2%、放血 +0.01%／點 | 命中當下（寫強度） | `Elem2.BleedPerLayer`／`BleedDrainPercent` | DLL命中 | perk | N3 |
| 血氣：扣血減半 | 自身計時／命中當下 | `Ctl.BloodCostScale` | Papyrus＋DLL | perk | N4 |
| 深創：上限 12 | 命中當下 | `Elem2.BleedCap` | DLL命中 | perk | N3 |
| 飲血：擊殺流血目標回血 20%＋嗜血 10 秒（命中 +20%、吸血 +10%） | 目標死亡 | `Elem2.OnKill`→`Ctl.SetBloodthirst` | DLL事件（套嗜血）＋DLL命中（讀） | 嗜血自身效果時長 | N5 |
| 血盾：吸血溢出轉臨時護盾（上限 20%） | 命中當下 | `Ctl.Leech` | 隨吸血處理者 | 自身護盾效果強度 | N2 |
| 吸血 +1%／點、逆流（反轉血位） | 命中當下 | `Ctl.GetBloodLeechRatio`／`BloodPercent` | DLL命中 | perk | N2 |
| 血承：擊殺流血目標吸收屬性 15 秒，只留最近一個 | 目標死亡 | `Ctl.ApplyInherit` | DLL事件 | 自身效果強度（多個值） | N5 |
| 止血：低血位時流血 ×1.5 | 兩可 | `Elem2.BleedTickMult`（`Status.Tick` 每秒依當下血位） | 兩可（見 3.1） | — | N3／每秒 |
| 血怒：中血位命中效果與吸血 +15% | 命中當下 | `Ctl.GetBloodHitMult` | DLL命中 | perk | N2 |
| 血海：同調三段血潮改範圍 | 狀態結束（切／融／期） | `React.EndBlood`（`SurgeRadius`） | DLL＋掃描 | — | N5 |
| 不死：同調三段維持扣血歸零；流血目標死亡回滿耐 | 自身計時＋目標死亡 | `Ctl.BloodDrainPerSecond`、`Elem2.OnKill` | Papyrus＋DLL事件 | GLOB | N5 |
| 開印流血 +1 層／每 5 點 | 狀態開始 | `Elem2.OpenStacks` | DLL命中 | perk | N3 |
| 開印回血：B_max ×0.5，低血位 ×2 | 狀態開始 | `Elem2.OpenBlood` | DLL命中 | — | N3 |
| 血臨強化：血臨後 10 秒不扣血 | 開關形態 | `Elem2.OnFormOpened`（SetNoBloodCost） | Papyrus | 自身視窗效果或 GLOB | — |
| 血咒：開印目標 5 秒回復速率 −50% | 狀態開始 | `Elem2.OpenBlood` | DLL命中 | 目標效果時長 | N3 |
| 血脈：開印 +2 同調 | 狀態開始 | `Elem2.OpenBlood` | DLL命中 | 同調效果強度 | N4 |
| 血祭之始：同調三段開印立即 ×0.5 血潮 | 狀態開始 | `Elem2.OpenBlood` | DLL命中 | — | N3 |
| 飽飲 ×1.5、治療倍率 +0.1／點、放血終焉 20%／6% | 狀態結束 | `React.EndBlood`、`Elem2.SurgeHealMult`／`SurgePercent` | 隨血潮處理者 | perk | N3 |
| 血漫：血潮時附近流血目標一起血潮 | 狀態結束（切／融／期） | `Elem2.EndBloodNodes` | DLL＋掃描 | — | N5 |
| 血斷：血印記融斷治療 50% | 結束-融斷 | `React.EndBlood` | DLL事件 | — | N5 |
| 血約：血終焉後 8 秒不扣血 | 狀態結束 → 自身計時 | `Elem2.EndBloodNodes` | 終焉處理者掛自身視窗；Papyrus 維持扣血時讀 | 視窗時長 | N3 |
| 血契：高血位（70% 以上）血終焉損 10%、血潮 ×2 | 狀態結束 | `React.EndBlood` | 隨血潮處理者 | — | N3（血位門檻與 1.1 不同，見 3.2） |
| 血引：血終焉後接管元素開印附流血 2 層 | 結束-被切 | `Elem2.OpenBlood` | DLL命中（同一擊） | — | N3 |
| 血池：融斷後 5 秒血池，你在其中每秒回血 | 結束-融斷 → 狀態每秒 | `Ctl.TickDomain` | Papyrus 每秒或 Hazard | — | N6 |

### 2.9 聖（2.3、2.6、5.9）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 聖印（目標受聖傷 +20%） | 狀態開始 | `React.Open`（聖印層數 kind 6，v0.3） | 引擎（印記效果＋0x1D） | 印記時長 | N3 |
| 聖印（開印）：你回血 B_max ×0.5、聖佑升一階 | 狀態開始 | `React.Open`（回血；無聖佑） | DLL命中 | 自身聖佑階 | N3 |
| 聖佑升階：命中帶神聖印記的目標（各階 8 秒；是否有 2 秒成熟見 3.2） | 命中當下 | **無**（現況有獨立的聖盾 +1，`Elem2.OnDivineHit`） | DLL命中 | 自身階效果＋時長 | N3 |
| 聖佑到期退一階 | 結束-過期 | 無 | DLL事件（否則 `ESSBTierDecay`） | 階時長 | N3 |
| 聖佑：武器傷害、聖傷、護甲加成 | 被動 | 無 | 引擎（0x23／0x1D 讀自身階） | 自身階 | — |
| 聖佑 II／III 命中回血 B_max ×0.25／0.5 | 命中當下 | 無 | DLL命中 | 自身階 | N3 |
| 聖佑 III 每擊聖光爆 B_max ×0.5（亡靈 ×3） | 命中當下 | 無（舊「神罰」讀聖印滿層） | DLL命中 | 自身階、目標印記 | N3 |
| 聖佑離開形態清空 | 開關形態 | 無 | Papyrus → DLL 原生函式 | — | N3 |
| 對亡靈魔族 ×1.5 | 命中當下 | `Elem2.DivineHitMult` | DLL命中（或 0x1D 分頁 2） | — | N2 |
| 裁決（終焉）：B_max ×2（乘聖佑聖傷）、亡靈 ×3、治療 B_max，不消耗印記 | 狀態結束（切／融／期） | `React.EndDivine`→`Elem2.JudgeArea`（並清聖印層） | DLL（被切命中；過期事件；融斷掃描） | 自身階 | N3／N5 |
| 化灰：死時帶神聖印記（白天必定） | 目標死亡 | `Elem2.ShouldAsh`（擊殺歸屬＝神聖） | DLL事件（判定）＋Papyrus `Ctl.ApplyAsh`（崩解） | 印記 | N5 |
| 持續新手主線：聖佑加成 +1%×階／點 | 被動 | 無 | 引擎 perk | perk | — |
| 護持：命中得 10% 魔抗 3 秒 | 命中當下 | `Elem2.OnDivineHit` | DLL命中（自身視窗） | 時長 | N3 |
| 驅魔：對死靈施法者 +50% | 命中當下 | `Ctl.IsNecromancer` | DLL命中（或 0x1D 分頁 2） | — | N2 |
| 神罰：聖光爆 ×0.5 → ×1.0 | 命中當下 | `Elem2.OnDivineHit`（舊語意） | DLL命中 | perk | N3 |
| 聖盾：聖佑各階受法術 −10／20／30% | 被動 | 現況是獨立聖盾階梯（`Ctl.AddHolyShield`） | 引擎 perk 讀聖佑階 | 自身階 | — |
| 命中回血 +2%／點 | 命中當下 | `Elem2.OnDivineHit` | DLL命中 | perk | N3 |
| 光耀：裁決後附近亡靈減速 | 狀態結束 | `Elem2.EndDivineNodes` | DLL＋掃描 | — | N5 |
| 聖灰：化灰時回魔 B_max ×2 | 目標死亡 | `Elem2.OnAsh` | DLL事件 | — | N5 |
| 祝福：命中時小範圍治療同伴 | 命中當下 | `Elem2.HealAllies` | DLL命中＋同伴掃描 | — | N5 |
| 庇護：生命 <30% 聖佑直接 III 並刷新，30 秒一次 | 自身門檻 | `Elem2.OnTick`（每秒；舊：聖盾滿層） | 兩可（見 3.1） | 30 秒冷卻效果 | N4／— |
| 天啟：同調三段裁決改範圍 | 狀態結束（切／融／期） | `Elem2.JudgeArea` | DLL＋掃描 | — | N5 |
| 神佑：同調三段致命傷留 1 血、2 秒無敵，每場一次 | 你被打（致命） | `Guard.OnHitEx`（lethal）＋`Ctl.RefreshDivineProtection`／`OnLethalHitWhileArmed` | Papyrus（`StartDeferredKill`） | 自身標記、`DivineArmed` GLOB | — |
| 淨土：同調三段神聖形態擊殺全化灰 | 目標死亡 | `Elem2.ShouldAsh`（看形態） | DLL事件 | GLOB | N5 |
| 開印回血 +5%／點 | 狀態開始 | `Elem2.OpenDivine` | DLL命中 | perk | N3 |
| 聖護：開印時 10% 魔抗 3 秒 | 狀態開始 | `Elem2.OpenDivine` | DLL命中 | 時長 | N3 |
| 聖臨強化：你與同伴回血 B_max ×2 | 開關形態 | `Elem2.OnFormOpened` | Papyrus（同伴掃描） | — | — |
| 聖痕：開印目標非亡靈也 +10% 聖傷 | 狀態開始 | `Elem2.IsHolyPrey` | DLL命中（目標效果）＋0x1D | 目標效果 | N3 |
| 聖光：開印時附近同伴回血 B_max | 狀態開始 | `Elem2.OpenDivine` | DLL命中＋同伴掃描 | — | N5 |
| 聖啟：同調三段開印聖佑直接 II | 狀態開始 | `Elem2.OpenDivine`（舊：對亡靈 ×0.5 裁決） | DLL命中 | 自身階 | N3 |
| 重裁 ×3、廣裁 3 公尺 | 狀態結束 | `Elem2.JudgeK`／`JudgeArea` | 隨裁決處理者 | perk | N3／N5 |
| 聖斷：融斷每目標治療 B_max | 結束-融斷 | `Elem2.EndDivineNodes` | DLL事件 | — | N5 |
| 聖域：聖終焉後 5 秒聖域（敵傷 −20%、你持續回復） | 狀態結束 → 狀態每秒 | `Elem2.EndDivineNodes`→`Ctl.StartDomain` | Papyrus 每秒或 Hazard | — | N6 |
| 淨灰：化灰爆聖光，附近亡靈受 B_max 聖傷 | 目標死亡 | `Elem2.OnAsh` | DLL事件＋掃描 | — | N5 |
| 處決：裁決處決範圍內 <20% 亡靈 | 狀態結束 | `Elem2.EndDivineNodes` | DLL＋掃描 | — | N5 |
| 聖引：聖終焉後接管元素開印治療 B_max | 結束-被切 | `Elem2.OpenDivine` | DLL命中（同一擊） | — | N3 |
| 神聖領域：融斷後 8 秒聖域；聖佑 III 時融斷不清空聖佑 | 結束-融斷 | `Elem2.EndDivineNodes` | DLL事件＋Papyrus 每秒 | 自身階 | N5／N6 |

### 2.10 毒（2.3、2.7、5.10）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 中毒：一顆效果，開印 3 劑 12 秒、命中 +1（重擊 +2）、時長 +3 秒，上限 10 劑／15 秒 | 命中當下 | `Ctl.HitStacks`→`AddStack` kind 7（**環狀桶、無上限、每層各自 12 秒**） | DLL命中（讀→加→覆寫重套） | 效果強度＋時長 | N3 |
| 中毒 DoT 每秒 | 狀態每秒 | `Status.Tick`→`Ctl.ApplyDotDamage` | 引擎 | 效果強度 | N3 |
| 中毒到期整顆消失 | 結束-過期 | `Status.Tick`（逐層老化） | 引擎 | 時長 | N3 |
| 淬毒（開印）：3 劑＋立即向 3 公尺內一人傳 1 劑 | 狀態開始 | `React.Open`→`Ctl.SpreadPoison` | DLL命中＋掃描 | — | N3／N5 |
| 瘴氣：≥5 劑時每秒傳 0.5 劑到 3 公尺（催毒時每秒 1 劑） | 狀態每秒 | `Status.Tick`（每 2 秒 1 層，`Elem3.SpreadInterval`） | 引擎（瘴氣披風）＋劑數併入要 DLL（見 3.1、4） | 披風存在、接收者中毒強度 | N3＋？ |
| 催毒（終焉）：剩餘期間強度 ×2、同一顆重套；融斷同樣；關形態後照跑 | 狀態結束（切／融／期） | `React.EndPoison`→`Ctl.SetCatalyzeOn`（**8 秒內每秒跳兩次**） | DLL（被切命中；過期事件；融斷掃描） | 中毒效果強度、時長 | N3／N5 |
| 死亡擴散：15 公尺、份額 max(剩餘, 最大生命 30%)×50%、鏈式每跳 50% | 目標死亡 | **無基礎版**（只有蔓延分支，`Elem3.OnKill`） | DLL事件＋掃描 | 屍體上中毒強度×剩餘 | N5 |
| 每劑 +2%／點 | 命中當下（寫強度） | `Elem3.PoisonTickMult` | DLL命中 | perk | N3 |
| 免疫：毒形態毒抗 +50% | 開關形態 | `Ctl.RefreshAbilities` | Papyrus（能力） | perk | — |
| 衰弱：≥5 劑攻擊 −15% | 命中當下（跨門檻） | `Elem3.OnPoisonHit` | DLL命中（跨 5 劑時掛標記） | 目標標記效果 | N3 |
| 毒皮：被近戰命中 → 攻擊者 +2 劑 | 你被打 | `Guard.OnHitEx`→`Elem3.OnPoisonSkin` | DLL受擊 | 攻擊者中毒效果 | N4 |
| 擴散間隔 −0.1 秒／點（2 → 0.5 秒） | 狀態每秒 | `Elem3.SpreadInterval`（兩檔 2／1 秒） | **不明**：披風每秒一跳，間隔縮不下去（見 3.2） | perk | — |
| 侵蝕：滿劑毒抗 −20% | 命中當下 | `Elem3.OnPoisonHit`（舊：≥10 層） | DLL命中 | 目標標記 | N3 |
| 傳染門檻：5 → 1 劑 | 命中當下（掛披風時） | `Elem3.SpreadThreshold` | DLL命中 | perk | N3 |
| 蔓延：死亡份額 50% → 75% | 目標死亡 | `Elem3.OnKill` | DLL事件 | perk | N5 |
| 以毒攻毒：你中毒時生命回復 +20% | 被動 | `Elem3.PoisonFormTick`（每秒） | 引擎（能力條件讀自身中毒關鍵字） | — | — |
| 瘟疫：同調三段中毒目標每秒自動擴散 1 劑（機率 5%／點） | 狀態每秒 | `Elem3.PoisonTickHook`（`Status.Tick`） | 見 4（需每秒點或套用事件） | perk | ？ |
| 百毒不侵：同調三段免疫中毒疾病；附近中毒敵人每秒替你回血 | 被動＋狀態每秒 | `Elem3.PoisonFormTick` | 引擎（免疫）＋Papyrus 每秒掃描或 DLL每秒 | — | ？ |
| 開印劑數 +1／每 3 點；劇毒之始 ×2 | 狀態開始 | `Elem3.OpenStacks` | DLL命中 | perk | N3 |
| 毒膜：開印時毒抗 +50% 5 秒 | 狀態開始 | `Elem3.OpenPoison` | DLL命中（自身視窗） | 時長 | N3 |
| 毒臨強化：範圍敵人 3 劑 | 開關形態 | `Elem3.OnFormOpened` | Papyrus → DLL 原生函式 | — | N5 |
| 腐蝕開印：開印目標毒抗 −10% | 狀態開始 | `Elem3.OpenPoison` | DLL命中 | 目標效果 | N3 |
| 毒血：開印回血 B_max ×0.5 | 狀態開始 | `Elem3.OpenPoison` | DLL命中 | — | N3 |
| 潰爛 ×3、延毒 +4 秒、毒斷（融斷）×4、傳奇主線催毒期間 +3%／點 | 狀態結束 | `Elem3.CatalyzeRate`／`CatalyzeSeconds`（舊語意：跳動次數、秒數） | 隨催毒處理者 | perk | N3／N5 |
| 瘴氣（分支）：毒終焉時把中毒（同強度同剩餘）複製到 6 公尺內敵人 | 狀態結束（切／融／期） | `Elem3.EndPoisonNodes` | DLL＋掃描 | — | N5 |
| 劇毒：催毒期間毒抗視為 0 | 狀態結束 → 狀態每秒 | `Elem3.ApplyVirulence`（套等量減抗） | 隨催毒處理者（套減抗效果，時長＝剩餘） | 目標效果 | N3 |
| 腐蝕終焉：毒終焉後魔抗 −20% 8 秒 | 狀態結束 | `Elem3.EndPoisonNodes` | 隨終焉處理者 | 目標效果 | N3 |
| 毒霧：融斷後 5 秒毒霧，內部每秒 +1 劑 | 結束-融斷 → 狀態每秒 | `Ctl.TickDomain` | 見 4（劑數併入） | — | N6＋？ |

### 2.11 水（2.3、2.6、5.11）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 浸濕（開印）：減速 15%、印記 10 秒 | 狀態開始 | `React.Open` | DLL命中 | 目標效果時長 | N3 |
| 浸濕 10 秒、命中刷新 | 命中當下 | `Status`（Wet） | DLL命中 | 時長 | N3 |
| 導引（終焉）：被切時接管元素下一次終焉 ×1.5；同調立即升一階 | 結束-被切（同調部分：三種結束是否都給不明） | `React.EndWater`（**+5 同調**，三種結束都給） | DLL命中（目標標記＋同調） | 目標「下一終焉」標記、同調強度 | N3／N4 |
| 長流：每秒回生命、耐力 2%＋ | 自身計時 | `Elem3.WaterFormTick`（控制器每秒） | Papyrus | perk | — |
| 長流回魔：維持費 80% | 自身計時 | **無** | Papyrus | 樹等級、GLOB | — |
| 浸濕持續 +0.3 秒／點 | 命中當下 | `Elem3.WetSeconds` | DLL命中 | perk | N3 |
| 清流：命中回耐 30 | 命中當下 | `Elem3.OnWaterHit` | DLL命中 | — | N2 |
| 長流 +0.2%／點、同調每段 +0.05%、長河（同伴） | 自身計時 | `Elem3.FlowPercent`／`WaterFormTick` | Papyrus | perk | — |
| 水壓：命中浸濕目標 +1，每層水附傷 +10%（+1%／點），上限 5／8，8 秒 | 命中當下 | `Elem3.OnWaterHit`＋`Status`（Pressure） | DLL命中 | 目標階（1～8） | N3 |
| 水膜：浸濕目標對你傷害 −10% | 被動 | 引擎 perk | 引擎 | — | — |
| 洗淨：命中清除自身一個負面，3 秒一次（淨化：全部） | 命中當下 | `Elem3.OnWaterHit`→`Ctl.ApplyCleanse`（PO3） | DLL命中（讀自身效果） | 自身 3 秒冷卻效果 | N4 |
| 水鏡：每命中 +1（最多 3）、8 秒 | 命中當下 | `Elem3.OnWaterHit`→`Ctl.AddWaterMirror` | DLL命中 | 自身效果強度、GLOB | N4 |
| 水鏡：被打 −1 並抵 30% | 你被打 | `Guard.OnHitEx`＋perk | DLL受擊＋引擎 perk | 同上 | N4 |
| 水體：同調三段受傷 −15%、火傷減半 | 被動 | 引擎 perk | 引擎 | GLOB | — |
| 浸濕減速 +1%／點 | 狀態開始 | `Elem3.WetSlow` | DLL命中 | perk | N3 |
| 湧泉：開印回耐 80 | 狀態開始 | `Elem3.OpenWater`（名稱仍是「回流」） | DLL命中 | — | N3 |
| 水臨強化：範圍浸濕減速＋你清除全部負面 | 開關形態 | `Elem3.OnFormOpened` | Papyrus → DLL 原生函式 | — | N5 |
| 沖刷：開印驅散目標一個有時限增益，每目標 10 秒 | 狀態開始 | `Elem3.OpenWater`→`Ctl.ApplyStrip` | DLL命中（讀目標效果） | 目標 10 秒冷卻 | N3 |
| 水牢：浸濕目標移速 −20% | 被動（浸濕存在） | `Elem3.OnWaterHit` | 引擎（浸濕效果帶 perk 條件減速） | — | N3 |
| 汪洋之始：同調三段開印的浸濕不過期直到被切 | 狀態開始 | `Ctl.SetWetLock` | DLL命中（給極長時長） | 時長 | N3 |
| 強引 ×2.0 | 結束-被切 | `Elem3.GuideMult` | 隨導引處理者 | perk | N3 |
| 潮引：接管元素 +5 → +10 同調 | 結束-被切 | `Elem3.GuideSync` | DLL命中 | 同調強度 | N4（與「升一階」衝突，見 3.2） |
| 水斷：水印記融斷改為治療你並回耐 | 結束-融斷 | `Elem3.EndWaterNodes` | DLL事件 | — | N5 |
| 汪洋：水終焉不移除浸濕、保留副印記 10 秒 | 結束-被切 | `Ctl.KeepAsSecond` | DLL命中 | 副印記時長 | N3 |
| 大潮：範圍內所有浸濕目標都給接管元素導引 | 結束-被切 | `Elem3.EndWaterNodes`→`Ctl.SetNextEndMultOn` | DLL命中＋掃描 | 目標標記 | N5 |
| 洗滌：水終焉清除你所有負面＋驅散目標一個增益 | 狀態結束（切／融／期） | `Elem3.EndWaterNodes` | 隨終焉處理者 | — | N3 |
| 潮池：融斷後 5 秒水域（減速 30%、你回血回耐） | 結束-融斷 → 狀態每秒 | `Ctl.TickDomain` | Papyrus 每秒或 Hazard | — | N6 |

### 2.12 暗（2.3、2.6、5.12）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 詛咒：開印 2、命中 +1，上限 5／10／13，每層抗性 −2%，8 秒 | 命中當下 | `Ctl.HitStacks`＋`Elem3.OnDarkHit`／`ApplyCurseErosion`（每擊重套侵蝕） | DLL命中 | 目標階（1～13，每階自帶抗性值） | N3 |
| 詛咒過期 | 結束-過期 | `Status.Tick` | 引擎 | 時長 | N3 |
| 詛咒（開印）：2 層＋吸魔 B_max | 狀態開始 | `React.Open` | DLL命中 | — | N3 |
| 死咒（終焉）：3 秒引信 → B_max ×2＋已損失 15%；期間無法治療 | 狀態結束（切／融／期）→ 結束-過期 | `React.EndDark`→`Status.SetDeathCurse`→`Status.Tick`（`ResolveDeathCurse`） | DLL（掛引信）＋DLL事件（引信到期結算；否則 `ESSBFuse`） | 引信效果強度＋時長 | N3 |
| 亡者歸來：死時帶黑暗印記 25%（化灰優先） | 目標死亡 | `Elem3.OnKill`→`Reanimate`（擊殺歸屬） | DLL事件（判定）＋Papyrus（復生、召喚上限） | 印記 | N5 |
| 維持費 2% | 自身計時 | `Rules.OnUpdate` | Papyrus | — | — |
| 抗性侵蝕 −0.2%／點 | 命中當下（寫強度） | `Elem3.ApplyCurseErosion` | DLL命中 | perk（13 階固定值如何吃點數不明，見 3.2） | N3 |
| 蝕魔：命中吸魔 ×2 | 命中當下 | `Elem3.OnDarkHit`（有基礎命中吸魔） | DLL命中 | — | N2（alter 沒有基礎命中吸魔，見 3.2） |
| 衰弱：詛咒目標攻擊 −10%；腐朽：回復速率 −50% | 被動（詛咒存在） | `Elem3.OnDarkHit`（每擊套） | 引擎（詛咒階帶 perk 條件效果） | — | N3 |
| 影甲：詛咒目標對你 −10% | 被動 | 引擎 perk | 引擎 | — | — |
| 詛咒滿層目標受所有傷害 +1%／點 | 被動 | `Elem3.TargetDamageMult`／`Ctl.ApplyDamage` | 引擎（0x1D／0x23 讀頂階） | 目標階 | — |
| 虛空：對魔力 <25% 施法者 ×1.5 | 命中當下 | `Ctl.GetHitMult` | DLL命中 | — | N2 |
| 收割：詛咒目標死亡回魔 | 目標死亡 | `Elem3.OnKill` | DLL事件 | 屍體上的階 | N5 |
| 深淵：同調三段上限 +1／每 3 點、滿層可侵蝕到負值 | 命中當下 | `Elem3.CurseCap` | DLL命中 | perk | N3 |
| 影身：同調三段被近戰 30% 下一擊無效並回魔 | 你被打 | `Guard.OnHitEx`→`Elem3.OnShadowBody` | DLL受擊 | 自身視窗 | N4 |
| 開印詛咒 +1 層／每 5 點 | 狀態開始 | `Elem3.OpenStacks` | DLL命中 | perk | N3 |
| 夢魘：開印恐懼 1.5 秒；群魔（範圍瘋狂） | 狀態開始 | `Elem3.OpenDark`→`Ctl.ApplyFear`／`ApplyFrenzy` | DLL命中（套效果；群魔要掃描） | 目標效果 | N3／N5 |
| 瘋狂：開印目標 3 秒攻擊最近任何人 | 狀態開始 | `Elem3.OpenDark` | DLL命中 | 目標效果 | N3 |
| 幻影：開印後 3 秒目標命中率 −30% | 狀態開始 | `Elem3.OpenDark` | DLL命中 | 目標效果 | N3 |
| 暗臨強化：範圍恐懼 2 秒 | 開關形態 | `Elem3.OnFormOpened` | Papyrus → DLL 原生函式 | — | N5 |
| 迷亂：開印目標 3 秒無法施法 | 狀態開始 | `Elem3.OpenDark` | DLL命中 | 目標效果 | N3 |
| 饕餮：死咒結算時吸血吸魔 B_max | 結束-過期（引信） | `Elem3.AfterDeathCurse` | DLL事件 | — | N3 |
| 不治：無法治療延長到 6 秒 | 狀態結束 | `Elem3.DeathCurseSeconds` | 隨死咒處理者 | perk | N3 |
| 蝕魔終焉：暗終焉後接管元素下一次終焉附吸魔 | 結束-被切 | `Ctl.SetPendingDrain` | DLL命中 | 目標標記 | N3 |
| 已損失係數 +0.5%／點 | 結束-過期（引信） | `Elem3.DeathCurseLostRatio` | DLL事件 | perk | N3 |
| 亡魂：死咒殺死目標 → 附近恐懼 2 秒 | 目標死亡 | `Elem3.OnDeathSoul`（傷害前預測） | DLL事件（死時看死咒標記） | 屍體上的引信 | N5 |
| 亡者強化：僕從繼承詛咒層、攻擊 +10%／層、持續 ×2 | 目標死亡 | `Elem3.Reanimate` | DLL事件（讀層數）＋Papyrus（復生） | 屍體上的階 | N5 |
| 處刑：死咒結算時 <15% 直接死亡（首領 ×3） | 結束-過期（引信） | `Elem3.AfterDeathCurse` | DLL事件 | — | N3 |
| 深淵回響：暗終焉回滿魔力 | 狀態結束（切／融／期） | `Elem3.EndDarkNodes` | 隨終焉處理者 | — | N3 |
| 死域：融斷後 5 秒死域（無法治療、每秒 B_max ×0.5） | 結束-融斷 → 狀態每秒 | `Ctl.TickDomain` | Papyrus 每秒或 Hazard | — | N6 |
| 死靈主：同調三段亡者歸來 100%、可永久 | 目標死亡 | `Elem3.Reanimate` | DLL事件＋Papyrus | GLOB | N5 |

### 2.13 星（2.3、2.6、5.13）

| 機制／節點 | 觸發類別 | 現在由誰跑 | 新架構由誰負責 | 狀態存在哪 | 切片 |
|---|---|---|---|---|---|
| 星痕：開印 1、命中 +1 並重新計時，上限 3／6／9 | 命中當下 | `Ctl.AddAstral`（`Status` 環狀桶，**每層各自 2 秒**） | DLL命中 | 目標階（1～9）＋時長 | N3 |
| 星痕 2 秒後全部一起引爆（層數 × B_max） | 結束-過期 | `Status.Tick`→`Elem3.DetonateAstral` | DLL事件（否則 `ESSBFuse`） | 階時長 | N3 |
| 星落（終焉）：B_max ×2；被切時接管元素這次開印 ×1.5 | 狀態結束（切／融／期） | `React.EndAstral`→`Elem3.Fall` | DLL（被切命中、同一擊給 ×1.5；過期事件；融斷掃描） | — | N3／N5 |
| 範圍主線每點 +1 公尺、夜晚範圍 ×1.5 | 被動（範圍計算） | `Elem3.Range` 等 | 各範圍處理者 | perk、GLOB | N5 |
| 星痕延遲傷害 +2%／點 | 結束-過期 | `Elem3.AstralTickMult` | DLL事件 | perk | N3 |
| 星輝：星形態魔力回復 +20% | 開關形態 | `Ctl.RefreshAbilities` | Papyrus（能力） | perk | — |
| 追擊：每第 3 次命中額外 35% 星傷 | 命中當下 | `Ctl.BumpAstralHits`／`Elem3.OnAstralHit` | DLL命中 | 自身計數效果強度 | N4 |
| 星軌：命中回魔 | 命中當下 | `Elem3.OnAstralHit` | DLL命中 | — | N2 |
| 星痕上限 +1／每 5 點 | 命中當下 | `Elem3.AstralCap` | DLL命中 | perk | N3 |
| 星痕弱點：重擊時每層 +8% | 命中當下 | `Ctl.GetHitMult` | DLL命中（或 0x1D） | 目標階 | N3 |
| 預知：星痕引爆前 1 秒你受傷 −20% | 兩可 | `Elem3.AstralForesee`（`Status.Tick`） | 兩可（見 3.1） | — | ？ |
| 星盾：星痕引爆時你得小護盾 | 結束-過期 | `Elem3.OnAstralDetonate` | DLL事件 | 自身效果 | N3 |
| 群星：同調三段星落連鎖附近星痕目標 | 狀態結束（切／融／期） | `Elem3.FallChain` | DLL＋掃描 | — | N5 |
| 星體：同調三段魔法傷害 −30%；星痕引爆治療你 | 被動＋結束-過期 | perk＋`Elem3.OnAstralDetonate` | 引擎＋DLL事件 | — | N3 |
| 星痕延遲 −0.1 秒／點 | 命中當下（套時長） | `Elem3.AstralDelay`（環狀桶只有 1／2 秒兩檔） | DLL命中 | perk | N3 |
| 星引力：開印回魔 | 狀態開始 | `Elem3.OpenAstral` | DLL命中 | — | N3 |
| 星臨強化：範圍敵人星痕 2 層 | 開關形態 | `Elem3.OnFormOpened` | Papyrus → DLL 原生函式 | — | N5 |
| 星鎖：開印目標 3 秒受所有元素傷 +10% | 狀態開始 | `Ctl.SetStarLock` | DLL命中（目標效果）＋0x1D | 目標效果時長 | N3 |
| 星光：開印時你受傷 −10% 3 秒 | 狀態開始 | `Elem3.OpenAstral` | DLL命中（自身視窗） | 時長 | N3 |
| 星耀：同調三段開印延遲星傷改立即 ×2 | 狀態開始 | `Elem3.OpenAstral` | DLL命中 | — | N3 |
| 隕星 ×3、流星雨（範圍）、範圍 +0.8 公尺／點 | 狀態結束 | `Elem3.FallK`／`HasMeteorShower`／`FallRadius` | 隨星落處理者 | perk | N3／N5 |
| 星斷：星印記融斷改真傷 ×0.6 | 結束-融斷 | `Elem3.HasTrueBurst` | DLL事件 | perk | N5 |
| 星引：星終焉後接管元素 +10 同調 | 結束-被切 | `Elem3.EndAstralNodes` | DLL命中 | 同調強度 | N4 |
| 星界之門：接管元素直接視為同調一段 | 結束-被切 | `Ctl.BoostSyncToStage1` | DLL命中（把計數設到一段門檻） | 同調強度 | N4 |
| 星軌終焉：接管元素開印 ×1.5 | 結束-被切 | `Elem3.TakeoverOpenMult` | DLL命中（同一擊） | — | N3 |
| 星域：融斷後 5 秒星域（受所有元素傷 +20%） | 結束-融斷 → 狀態每秒 | `Ctl.TickDomain`＋`Elem3.TargetDamageMult` | Papyrus 每秒或 Hazard（每秒掛目標標記，0x1D 讀） | 目標標記 | N6 |

---

## 3. 兩邊都說得通的（需要使用者裁決）

### 3.1 觸發點可以放在兩個地方的機制

| # | 機制 | 選項 | 玩家感覺 | 成本 | 建議 |
|---|---|---|---|---|---|
| 1 | **血的吸血**（1.1：命中流血目標，占附傷） | (a) 命中當下，DLL 算附傷時一起回血（N2）；(b) 血痕過期或血潮結算時回；(c) 血痕每跳回一點 | (a) 砍一刀回一口，跟血位曲線同步，最直覺；(b) 延遲、跟打擊脫節；(c) 停手也在回，比較像「吸血鬼光環」 | (a) 零額外面；(b) 要過期事件；(c) 要 DLL 每秒點，或每層 DoT 帶一顆「治療施法者」效果（引擎做不到） | **指揮官建議**：基礎吸血走 (a)（N2，DLL）；血潮保留結算時的治療；(c) 列為候選，看放血需要的 DLL 每秒點做不做得出來再決定 |
| 2 | **放血**（當下生命 0.3%／層／秒） | (a) DLL 每秒掃描，讀當下生命；(b) 命中時以當時生命換算成固定每秒值 | (a) 目標越掉血放血越小，對高血目標最快（v0.3 原意）；(b) 停手後放血數值固定，直到血痕結束 | (a) 新的每秒執行點（全案崩潰面最大的一塊）；(b) 零 | 已裁決「能每秒就還原」；建議先做 (b)，把 (a) 綁在每秒點的查證結果 |
| 3 | **止血**（低血位流血 ×1.5） | (a) 套血痕時依當下血位寫進 DoT 強度；(b) 每秒依當下血位調整 | (a) 血位變了要等下一刀才更新；(b) 即時跟隨 | (a) 零；(b) 每秒點 | (a)，與放血同一個每秒點再議 |
| 4 | **火：自動洩壓**（生命 <10%） | (a) Papyrus 每秒（跟火源代價同一個 tick）；(b) DLL 受擊時判定（N4）；(c) 兩者都掛 | (a) 最多晚 1 秒；被一刀打到 <10% 到洩壓之間可能再被過熱判定；(b) 被打那一幀就洩；但代價本身扣到 <10% 時沒有受擊，(b) 抓不到 | (a) 零新面；(b) 受擊 sink 內多一次比較 | **(c)**：代價是 Papyrus 每秒扣，所以 (a) 必須有；(b) 補「被打到 <10%」的同幀 |
| 5 | **冰心、庇護**（生命 <30%，30 秒一次） | (a) Papyrus 每秒輪詢（現況）；(b) DLL 受擊時判定 | (a) 晚 ≤1 秒；(b) 被打那一幀觸發；維持費或火源代價造成的跌落抓不到（冰與聖沒有這種代價，所以差別小） | (b) 受擊 sink 內一次比較 | (b)（N4），因為這兩個元素只有被打才會掉血；維持費不扣生命 |
| 6 | **雷神**（同調三段電荷滿層自動放電＋回魔） | (a) 命中當下：電荷一到滿就放（對被命中的目標）；(b) 每秒輪詢，對最近的帶雷印記目標（現況 `Elem.OnTick`） | (a) 第 6／10／13 下同幀爆，節奏清楚；(b) 滿了之後最多等 1 秒、目標可能不是你在打的人 | (a) 零；(b) 需要每秒點或 Papyrus 每秒呼叫 DLL | (a)，也把「放電對象」定為被命中目標 |
| 7 | **雷雨每 3 秒 +1 電荷** | (a) Papyrus 3 秒計時呼叫 DLL 原生函式改電荷效果；(b) DLL 每秒點；(c) 命中時依「距上次補電過了幾個 3 秒」補算（讀電荷效果已過時間） | (a)(b) 不打也在充；(c) 只在命中時才看得到電荷跳上來 | (a) 一個原生函式；(b) 每秒點；(c) 零 | (a)；DLL 原生函式本來就要為切換／融斷等 Papyrus 入口準備 |
| 8 | **火浴**（白熱期間火源每燒到一人回血 B_max ×0.1／秒） | (a) DLL 每秒數 3 公尺內敵人；(b) 白熱時掛一顆自身「回血」效果，強度在升白熱時按當時人數寫死；(c) 改成「命中時回」 | (a) 準確；(b) 人數變了不跟著變；(c) 手感變成吸血 | (a) 每秒點；(b)(c) 零 | (b)，並請使用者確認能接受「人數在點燃時定」 |
| 9 | **火域：白熱引信暫停** | (a) 每秒把白熱時長往後推（DLL 每秒或 Papyrus 每秒呼叫原生函式）；(b) 進入火域時一次延長 5 秒 | (a) 真的暫停；(b) 近似，離開火域也多了幾秒 | (a) 每秒；(b) 零 | (b) |
| 10 | **預知**（星痕引爆前 1 秒受傷 −20%） | (a) 命中套星痕時同時掛 2 秒自身減傷（整段都減）；(b) 每秒檢查誰的星痕剩 ≤1 秒 | (a) 比原文多減 1 秒；(b) 準確但最多晚 1 秒 | (a) 零；(b) 每秒點 | (a) |
| 11 | **瘴氣／瘟疫／毒霧的「+劑」** | (a) 引擎披風每秒對鄰居套一顆小法術，DLL 接「效果套用事件」把它併進鄰居的單一中毒；(b) DLL 每秒點；(c) Papyrus 每秒呼叫 DLL 原生函式 | 三者手感相同（每秒一次） | (a) 新的事件 sink（不在任何切片）；(b) 每秒點；(c) 回到每秒掃描 | 先查證 (a)；不行走 (c)。注意 latency 4.11 說「引擎自己傳」，但單一成長效果的「+劑」引擎自己做不到 |
| 12 | **導引的「同調升一階」** | (a) 只在被切時（接管元素存在時）；(b) 三種結束都給（現況 +5 同調三種都給） | (a) 水只有在切換時有用；(b) 關形態或停手也拿同調，但關形態時同調本來就要歸零 | 零 | (a)，融斷給同調沒有意義 |
| 13 | **化身**（每 30 秒觸發當前元素持續傳奇效果） | (a) Papyrus 30 秒計時；(b) 30 秒冷卻效果到期由 DLL 事件觸發；(c) 冷卻好之後的下一次命中觸發 | (a)(b) 不打也觸發；(c) 綁在攻擊上 | (a) 零；(b) 要過期事件；(c) 零 | (c)，且需要先定義每個元素的「持續傳奇效果」是什麼（見 3.2） |

### 3.2 設計本身的歧義（寫表時沒辦法決定，照原文標在列上）

1. **雷 N 的定義**：總表第 5 條與 2.1 寫 N＝1＋電荷數（期望到 23.79），5.5 內文仍寫 N＝1＋電荷階（四階、期望 13／17.3／19.5／20.8）並自己標「未解決」。
2. **放電在過期與融斷時吃不吃重擊倍率**：那一刻沒有命中；現況讀「上一擊是不是重擊」。
3. **過載終焉「終焉時電荷 ≥8」**：只限雷終焉，還是任何元素的終焉（電荷在你身上）？現況只算雷。
4. **電弧**與**寒蝕**：分支內容（跳 2 人 40%、重擊凍結 +2）跟還原後的基礎規則一模一樣，等於零效果；現況把電弧實作成 80%。
5. **震擊「消耗滿層裂痕」**：裂痕是單層標記，沒有「滿層」。
6. **冰心「帶寒意的敵人」**：寒意是舊三階的第一階，凍結量表還原後沒有這個名詞（凍結 ≥1？）。
7. **冰崩**：「碎冰改 3 公尺」只套在終焉的碎冰，還是也套在「冰封中第一擊」的碎冰？
8. **不移**：alter 沒有任何「被打斷或擊倒會失去同調」的規則，這個分支沒有東西可以保護。
9. **暗「蝕魔：命中吸魔 ×2」**：alter 的基礎只有開印吸魔，沒有命中吸魔（現況有）。
10. **詛咒抗性侵蝕的點數成長**：compromises A3 採「13 顆階 MGEF 各帶固定抗性值」（因為多效果強度覆寫未查證），那「−0.2%／點」與「深淵可到負值」要怎麼進固定值的階？
11. **毒「擴散間隔 −0.1 秒／點（2 → 0.5 秒）」**：改成每秒一跳的瘴氣披風之後，間隔縮不下去；這條主線需要改寫。
12. **聖佑有沒有 2 秒成熟**：總表第 8 條寫「各階 8 秒、成熟 2 秒」，5.9 的表與內文沒有成熟。
13. **血位門檻**：1.1 的四段是 85／50／20，5.8 的止血「30% 以下」、血怒「30～70%」、血契「70% 以上」還是舊的三段數字。
14. **白熱火源披風的強度誰寫、何時寫**：2.7 說「由腳本在升到白熱、生命上限改變、投點時算一次」，但升白熱發生在 DLL 命中內；披風關聯法術能不能用強度覆寫參數套用未查證。
15. **反咒**（目標施法時）：沒有任何 DLL 切片處理「敵人施法」事件，只能留 Papyrus（現況靠動畫事件）。
16. **浸濕與水印記**：兩者都是 10 秒、都在開印掛上，文件把它們當兩個東西（2.3 浸濕是狀態、2.2 水印記 10 秒），「浸濕持續 +0.3 秒／點」要不要連印記一起延長？
17. **化身**：各元素的「持續傳奇效果」有些是被動數值（絕對零度、深淵），不是可以「觸發一次」的東西。

---

## 4. 需要 DLL 每秒執行點的

每秒點**尚未查證**（C++ 沒有 hook 就沒有原生計時；候選做法是每幀任務自我重排，或引擎更新 hook）。文件之間的歸屬也不一致：compromises 把放血放 N5，latency 第 6 節把每秒計時放 N6，而且說「留在 Papyrus」。

**只有每秒點才做得到（沒有等價替代，只有降級）**

| 機制 | 沒有每秒點時的降級 |
|---|---|
| 放血依目標**當下**生命（A1b） | 命中時以當時生命換算（已裁決可接受） |

**每秒點是選項之一，另有未查證或較差的替代**

| 機制 | 替代 |
|---|---|
| 瘴氣（≥5 劑每秒傳 0.5 劑，催毒時 1 劑） | 效果套用事件 sink（未查證、不在任何切片），或 Papyrus 每秒呼叫 DLL 原生函式 |
| 瘟疫（同調三段每秒機率擴散 1 劑） | 同上 |
| 毒霧（領域內每秒 +1 劑） | 同上 |
| 百毒不侵（附近中毒敵人每秒替你回血） | Papyrus 每秒掃描 |
| 止血（流血強度跟當下血位） | 套用時寫死 |
| 血「每跳吸血」（候選，3.1 第 1 項） | 不做，維持命中吸血 |
| 火浴（依火源燒到的人數每秒回血） | 點燃時人數寫死 |
| 火域白熱引信暫停 | 進入時一次延長 |
| 預知（引爆前 1 秒） | 掛 2 秒整段減傷 |
| 雷雨每 3 秒 +1 電荷 | Papyrus 計時呼叫 DLL 原生函式 |
| 雷神（若選每秒輪詢） | 改成命中當下 |

**已經不需要**：電荷「10 秒後每秒 −1」（已折衷為到期歸零）。

**每秒但留 Papyrus、不依賴 DLL 每秒點**：維持費、魔力歸零關閉、血維持扣血、火源代價、自動洩壓的每秒那一半、長流（含回魔、長河）、環境偵測、化身計時、神佑脫戰重置、風潛行能力切換、所有領域（除了毒霧的「+劑」；也可改 Hazard，N6 選配）。

結論：**真正綁死在 DLL 每秒點上的只有放血一項**，而且它有已裁決的降級。另外 11 項如果每秒點做不出來，都有替代；其中影響最大的是毒的三項「+劑」，因為它們牽涉到「單一成長效果」怎麼被披風或領域加劑，需要一個還沒排進切片的事件 sink 或原生函式。

---

## 5. alter 與程式不一致的地方（只報告，不修）

現況程式是 round 18／19 的狀態：DLL 只做了 N1（附傷），其他全部仍是 v0.3 時期的 Papyrus 實作。所以大部分不一致是「alter 的改動還沒落地」，不是 bug。

**alter 已改、程式還是舊設計**
1. **火**：程式是目標熱度 0～10、滿即自燃、同調三段後累積自身過熱（`Elem.HeatCap`／`OnIgnite`、`Ctl.AddSelf` kind 4）；alter 是自身熱度三階、白熱火源、引信過熱、爆燃吃其他元素狀態。火源、代價、自動洩壓、熔燒在程式裡都不存在。火樹的添薪、熔心、火浴、熔爐、洩壓、熾焰、火域的程式語意全是舊版。
2. **碎冰**：程式只在終焉碎冰，冰封且 <20%（銳碎 30%）處決、否則 ×2.5（`Elem.Shatter`）；alter 是冰封中第一擊 20% 最大生命真傷（首領 10%）、一次冰封一次、銳碎改 25%。冰棺沒有「第二次 ×0.5」。
3. **神聖**：程式是目標聖印層數（kind 6）、獨立的聖盾階梯（`Ctl.AddHolyShield`），庇護是「聖盾滿層」、聖啟是「對亡靈 ×0.5 裁決」；alter 是自身聖佑三階，聖盾併入、庇護改聖佑 III、聖啟改聖佑 II。
4. **毒**：程式是環狀桶毒層（無上限、每層各自 12 秒）、催毒＝8 秒內每秒跳兩次、每 2 秒傳 1 層、沒有基礎的死亡擴散；alter 是一顆成長效果（10 劑／15 秒）、催毒 ×2、瘴氣披風、死亡擴散是基礎規則。
5. **風多段觸發**：程式沒有（`React.EndWind`）；關閉專精主線在程式仍是吹飛距離 +0.2 公尺（`Elem2.BlowDistance`）。
6. **死亡機制**：化灰與亡者歸來在程式仍用 round 14 的擊殺歸屬（`Ctl.KillElementFor`／`LastDamageFor`、`Elem2.ShouldAsh` 看「致死元素是否神聖」）；alter 刪除擊殺歸屬，改看屍體上的印記。另外 `Ctl.OnKillEvent` 只在殺手是玩家時才處理（alter 沒寫這個限制）。
7. **印記上限**：程式仍是 8 格登記表；alter 已取消上限。
8. **水導引**：程式給 +5 同調（潮引 +10）且三種結束都給；alter 是「同調立即升一階」。長流回魔（維持費 80%）程式沒有；「回流」改名「湧泉」程式仍叫回流（只影響顯示文字）。
9. **電荷衰減**：程式是 10 秒後每秒 −1（`Ctl.Tick`）；alter 折衷為到期歸零。
10. **星痕**：程式是每層各自 2 秒引爆（v0.3 原設計）；alter 折衷成一起引爆、命中重新計時。
11. **冰盾**：alter 是每命中 +1（最多 5）、8 秒；程式只有「冰甲」開印給 1 層，沒有每擊 +1，也沒有 8 秒時限。
12. **環境**：程式把所有室外雨雪都當成「暴風雪／雷雨」（`Ctl.EnvCheck`：分類 2、3 都設 stormy）；alter 分開普通雨雪（視為浸濕）與暴風雪（凍結 ×2）、雷雨（電荷）。

**alter 已改、DLL N1 還沒跟上（排在 N2）**
13. 重擊與潛行：alter 要 HitData 旗標（65536／2048）；DLL N1 用 `IsPowerAttacking`／`IsSneaking` 條件選法術（Plugin.cpp 的 static_assert），Papyrus 側則用旗標，兩邊判定不同。
14. 每擊隨機 B、雷 best-of-N、血位線性：N1 是固定平均值、雷五檔 N=1、血四段（`HitPipeline.h` 的 `kBloodThresholds`、`kLightningChance`）。

**程式反而比 alter 更接近 v0.3 原意的**
15. 放血：程式在 `Status.Tick` 每秒讀目標**當下**生命扣，正是 alter 想還原、但要看 DLL 每秒點才能保留的行為。搬到新架構時如果每秒點做不出來，這一項會從「已有」退成「命中時換算」。
16. 同調：程式已是命中計數 5／15／30（`Ctl.AddSync`／`ComputeSyncStage`），與還原後的 alter 一致（只是計數存在腳本變數與 GLOB，不在效果強度）。

**文件之間的不一致（附帶）**
17. 5.3 開頭說火源每秒 `B_max ×0.5 × G(L)`，2.7 與總表第 2 條是 `(B_max ×0.25 × G + 代價 × N) × M_mod`。
18. 5 節開頭的改寫原則仍說「每 N 次命中類節點一律〔取代〕成機率或時間視窗」，與總表第 14 條（全部還原 v0.3 計數）矛盾。
19. 2.7「magnitude 在玩家狀態改變時重寫、T 由引擎選法術版本」與 2.13「你身上的資源由腳本在命中事件裡推進」是 N1 之前的描述，與 N2～N4 的分工不符。
20. 放血的每秒點：alter 2.3 說「計畫 N5」，latency 第 6 節 N6 說每秒計時留 Papyrus，compromises 說 N5——三處說法不同。
21. latency 4.2 的對照表裡，電荷、岩甲、風勢、冰盾、水鏡、詛咒、星痕、戰意、水壓仍寫舊的三階梯與成熟秒數，只有血痕與同調更新成還原後的層數。
