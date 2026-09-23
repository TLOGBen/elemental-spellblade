# 設計：附傷走引擎、目標狀態走引擎——延遲與「不可能狀態」的一次解法

- 撰寫時間：2026-09-20 17:00（Asia/Taipei，`Get-Date` 實查）；本檔在同日稍後依指揮官追加的三道指令擴寫（目標狀態層重設計、取消疊層、產出 `元素魔戰士規劃-v0.3_alter.md`）。
- 收尾（同日 22:30）：火的四項裁決（生命 <10% 自動洩壓、過熱走代價路徑且洩壓優先、火源 = 基礎燃燒 + 代價×N 再乘 M_mod、白熱全身火焰著色器例外）已併入；alter 開頭的清單已全部定案，本檔與 alter 沒有任何「待核准」「備選」「兩種讀法」。
- 追加（同日 21:30 後）：`.codex/design-decisions-pending.md` 的九項使用者決定已併入（毒素單一成長效果與死亡全場擴散、冰封碎冰真傷、死亡機制改看印記並刪除擊殺歸屬、神聖自身階梯、雷 best-of-N、風終焉多段觸發、武器限定視覺、無轉場、熱鍵預設開）。本檔先前提議的「最後一擊標記」已撤銷。
- 性質：給實作代理的計畫。本次只建立／修改兩個檔案：本檔與 `元素魔戰士規劃-v0.3_alter.md`。沒有建置、沒有編譯、沒有進遊戲、沒有連網，沒有碰 `元素魔戰士規劃-v0.3.md`。
- 設計真相：**規則以 `元素魔戰士規劃-v0.3_alter.md` 為準**（待使用者核准）；本檔只寫「引擎做什麼、Papyrus 做什麼、生成器吐什麼、刪什麼、怎麼分期、怎麼驗收」，不重複設計內容。alter 檔開頭的「需要使用者確認的改動」是使用者要逐條核准／否決的清單。
- 讀過的東西（唯讀）：`src/*.psc`、`build_v03.py`、`settings.json`、`build/state_schema.py`、`元素魔戰士規劃-v0.3.md`、`實作紀錄.md`（搜尋）、兩份 review、`.codex/fix-round17-briefing.md`、`.codex/smoke5-Papyrus.0.log`（grep）、`vendor/wbDefinitionsTES5.pas`、`vendor/imports/{Actor,ActiveMagicEffect,Spell,PO3_SKSEFunctions,CustomSkills}.psc`、`vendor/skse64.zip`（找 `DoCombatSpellApply` 實作，沒找到）、本機 `SkyrimSE/Data/Skyrim.esm`、`MO2/mods/战斗相关-Ordinator-技能树大修/Ordinator - Perks of Skyrim.esp` 與其 BSA 的檔名／字串表、`MO2/mods/新魔法-Phenderix Elements/Phenderix Elements.esp`、`MO2/mods/Phenderix Elements/scripts/Source/*.psc`。
- 信心標記：**high** = 從檔案或本機 ESM/ESP 位元組直接證實；**medium** = 有原版／Ordinator 用例可推論但沒有引擎原始碼；**low** = 只能進遊戲才知道。
- 與 fix round 17 的關係：round 17 簡報要的便宜修法（Guard 早退、跨實體減量）在第 12 節，與本計畫第 1 期重疊，不必做兩次；第 2 期以後是結構替換，要先過使用者核准。

---

## 1. 判決

**兩件事都要換，而且是同一個方向：把「命中那一幀必須發生的事」和「目標身上的狀態」全部交給引擎，Papyrus 只留「晚到也無妨」的反應與帳。**

1. **附傷走引擎。** 每次武器命中的元素點傷由隱藏 PERK 的「Apply Combat Hit Spell」（索引 51，`vendor/wbDefinitionsTES5.pas:4564`）以玩家為施法者套用自有法術；magnitude 只在玩家狀態改變時由腳本寫入。理由是鎖，不是指令數：`smoke5-Papyrus.0.log` 兩次含我們事件的 dump（04:30:17、04:33:05）裡 **214 個 suspended stack 有 201 個、204 個有 196 個是我們的**（94–96%），卡在 `ESSBGuard.psc:89`（262）→ `ESSBController.psc:7366`（241）→ `3342`（251）→ `ESSBTrees.psc:1099`（158），與附傷本體 `ESSBController.psc:1726 → 1797 → 2972`（28／27／23）。每一刀要穿過 Guard → Controller → Trees 三個實體的鎖，而 Controller 同時在跑 Tick；一個實體一次只跑一條 stack，等鎖就是玩家感覺到的延遲。原版 `TrickShot`／`HackAndSlash`／`Limbsplitter`、Ordinator 129 段、Phenderix `ZZPerk_PoisonParalyze` 都用這個進入點，法術形狀（type 0／casting 1／delivery 1）與我們的 `ESSB_Hit_*` 完全一樣（high）。
2. **目標狀態走引擎，並且取消疊層。** 今天的狀態層是一個腳本容器（`ESSBStatus`：三個環狀桶、38 個 Int、24 個 Float）掛在 30 秒宿主上，每 25 秒匯出→存進控制器的 bank→驅散→重掛→匯入，另有 96 格待綁定緩衝與 8 格登記表。本場 log 證明它會組出**不可能的狀態**（第 2 節）。改法不是修那一格索引，而是讓每一種狀態變成目標自己身上的一顆 MGEF：短階梯（2～4 階互相取代，頂階＝原本的「滿層」事件）或原版意義的 DoT。引擎自己管持續、取代、過期；腳本只在效果的開始／結束回呼裡做反應。沒有匯出匯入，沒有 slot，沒有 pending，沒有上限——這整類 bug 在結構上不再可能（第 8 節的不變量）。
3. 兩件事在同一個 PERK 上會合：命中時引擎依「目標身上是哪一階」選附傷法術的版本或乘法術強度（alter 2.7 的 T），並套用印記與升階；腳本不在命中路徑上做任何決定。唯一例外是使用者定案的中毒「強度與時間一起長」（決定 1）：它需要讀目標身上那顆效果再重套，是腳本，但無狀態、排在引擎附傷之後、只在毒形態（第 8 節第 8 條）。
4. 死亡機制改看印記（決定 4）後，整套擊殺歸屬刪除，本檔早先的「最後一擊標記」也撤銷；引擎持有的印記就是唯一證據。

---

## 2. 對 `180126` 的診斷：是哪一類缺陷

**觀察（high，直接 grep）**：整份 log 只有 54 行 `[ESSB]`，全部落在 04:42:35–04:43:31（除錯等級在最後一分鐘才開）。所以「整場沒有 `[Hit]` 行」不能證明沒打過它——但下面這些值本身就是證明：

```
04:42:46 [ESSB][damage][L3] 180126 element=8 amount=827.999939
04:42:47 [ESSB][astral][L1] 180126 detonate layers=60
04:42:47 [ESSB][status][L3] 180126 ... poison=180 astral=0 ... wetlock=30
04:42:54 [ESSB][damage][L3] 180126 element=8 amount=1872.000000
04:42:55 [ESSB][status][L3] 180126 ... poison=36 ... wetlock=30
04:42:56 [ESSB][status][L3] 180126 ... poison=0 ... wetlock=30
04:43:27 [ESSB][damage][L3] 180126 element=8 amount=1511.999878
04:43:28 [ESSB][astral][L1] 180126 detonate layers=60
04:43:29 [ESSB][status][L3] 180126 ... poison=144 ... wetlock=30
```

**為什麼是不可能的狀態（high，對照原始碼）**
- `wetlock` 只可能是 0 或 1：`SetWetLock`（`ESSBStatus.psc:607-608`）寫 1、`ReleaseWetLock`／`ClearStack(8)`（`596-599`、`448`）寫 0。唯一能寫入其他值的地方是 `ImportState`（`ESSBStatus.psc:743`：`WetLock = aiInts[ESSBState.TailOffset() + 7]`）。
- `astral` 引爆 60 層：`AddAstral`（`476-498`）以 `Cap(11, 3)` 夾住（`ESSBElem3.AstralCap` 最多 9）；60 只可能來自 `ImportState` 的 `AstralRing[0/1] = aiInts[30/31]`（`733-734`）。
- `poison=180` 在 10 秒內掉到 36 再到 0，代表桶子集中在**最舊**的幾格（`RingAge`，`233-242`）——同樣只有匯入能一次放進舊格。
- 三個值都是 30 或 30 的倍數（6×30＝180、2×30＝60、30）：與「匯入的 38 格 Int 陣列前 24 格是 0、後 14 格是 30」完全一致。任何合法的 `AddStack`／`SetStack`（`268-345`、`353-387`）都做不出這個形狀。

**缺陷的類別**：**跨腳本實體、以位置為索引的手工序列化**。目標狀態被匯出成 `Int[38] + Float[24]`（`ExportInts`／`ExportFloats`，`643-709`），存進控制器的四個 bank（`SwapIntBank`／`StoreSwapInts`／`SaveSwapData`／`ReadSwapInts`，`ESSBController.psc:6294-6353`，用 `(slot % 2) * 38 + index` 與 `(slot % 4) * 24 + index` 定址），再由**另一個** AME 實體在 `OnStatusStart`（`2491-2544`）憑 `BackupValid[slot]` 匯入；版面常數散在三個檔（`ESSBState.PoisonOffset/TailOffset/IntCount`、`ESSBStatus.ImportState` 的固定索引、`ESSBController` 的 bank 步幅），還有一條 27→38 的升版路徑（`UpgradeInts`、`InitBackupInts` 6221-6293）。身分檢查（slot／actor／generation）和資料本身是分開的：只要任何一步的索引、步幅、版面或時序錯了，一具目標就會拿到「不屬於它的位元組」，而匯入之後它和真實狀態無法區分。要指出是哪一個索引錯只能靠離線重演（把 log 的值餵進 `fix15_verify.py` 同款的 harness），本檔不假裝知道；**但修法不是找那個索引，是讓這條鏈不存在**。引擎自己持有的 ActiveMagicEffect 沒有匯出匯入，狀態值就是效果的 magnitude 與 duration，永遠掛在它自己的目標上。

**順帶的第二個高信心發現**：`build_v03.py:766` 把 `693` 當成 `HasMagicEffectKeyword`；本機 `vendor/wbDefinitionsTES5.pas:2707,2712` 與 `Skyrim.esm`／Ordinator 的 PERK 位元組都說 **693 = `EPMagic_SpellHasKeyword`（只在法術類進入點的法術分頁有意義），699 才是 `HasMagicEffectKeyword`**（Ordinator `ORD_Hea60_BreakUponMe_Perk_60` 在 0x24 分頁 1 用 699）。所以現行的浴火（`build_v03.py:875-878`）、水膜（`938-941`）、影甲（`950-953`）三段條件極可能從未成立。第 12 節列為便宜修法。

---

## 3. 目標架構總覽

| 層 | 引擎（零 Papyrus） | Papyrus（晚到也無妨） |
|---|---|---|
| 附傷 | `ESSB_P_HitProc` 的「Apply Combat Hit Spell」段套 `ESSB_Hit_*`；抗性、Ordinator 天賦、學派經驗、命中特效 | `RefreshProcMagnitudes()` 在狀態改變時寫 magnitude |
| 目標階倍率（alter 2.7 的 T）、目標狀態放大武器傷害 | 「Mod Spell Magnitude」（0x1D）與「Mod Attack Damage」（0x23）段，分頁 2 讀目標身上的階（HasMagicEffect 214） | 無 |
| 印記 | 同一 PERK 的兩段／元素：目標沒有 `ESSB_Mark_X` → 套「開印版」；有 → 套「刷新版」。印記帶 `ESSB_MarkAny` 並驅散同關鍵字 → 新元素自動切掉舊元素 | `ESSBMark` 在 `OnEffectStart`（開印版）觸發開印反應、`OnEffectFinish` 分辨被切掉／過期／融斷並觸發終焉 |
| 目標階梯（凍結、血痕、水壓、詛咒、星痕）與中毒單一效果 | 每階一顆 MGEF；升階／刷新／頂階各一段進入點，條件是「有第 k 階」與「第 k 階的成熟計時還在不在」；DoT 由引擎逐秒扣；引信到期由引擎結束效果 | 頂階事件與引信到期的**效果**（自燃傷害、死咒傷害、星痕傷害、擴散）由該效果自己的腳本在 `OnEffectStart`／`OnEffectFinish` 呼叫控制器；擴散是中毒 II 以上效果自己的 `OnUpdate`（無狀態，只找一個鄰居） |
| 單階標記（裂痕、失衡、浸濕、破魔印、星鎖、浮空、已交戰、聖印、黑暗印記） | 引擎（已交戰直接嵌進附傷法術） | 浮空到期的落地傷害由效果腳本觸發 |
| 中毒〔決定 1、2、5；N3 起由 DLL〕 | 一顆 DoT，引擎逐秒扣；≥5 劑時另掛「瘴氣」披風（原型 35，3 公尺，關聯法術每秒對鄰居套 0.5 劑），引擎自己傳 | DLL 在命中時讀效果的 magnitude／剩餘秒、算新值、以 magnitude 覆寫重套；死亡分發在 N5 的死亡事件；N3 之前的 Papyrus 版見第 8 節 |
| 碎冰〔決定 3、6〕 | 冰封 T3 是引擎效果 | 命中冰封目標的第一擊：腳本 `ApplyTrueDamage(最大生命 × 20%／10%)` 並驅散冰封（永凍→套凍結） |
| 聖佑〔決定 8〕 | 三顆自身階效果；0x23／0x1D 段讀 `HasMagicEffect(聖佑 T{k})` 給武器與聖傷加成 | 命中帶神聖印記目標時升階；每階到期由該階的小腳本套低一階 |
| 雷 best-of-N〔決定 7〕 | 五檔法術 × 電荷階 × 攻擊變體的機率條件段 | 無 |
| 風終焉多段〔決定 9〕 | 無 | 風印記被切掉時，`ESSBMark`（風）在 finish 回呼裡對接管元素多套 N−1 次命中效果（傷害 ×0.5、階梯免等待、雷各自擲骰） |
| 你身上的資源（電荷、岩甲、起風、過熱、戰意、冰盾／水鏡／聖盾、同調） | 每階一顆 MGEF；PERK 條件讀它們的存在 | `OnWeaponHit` 裡「存在測試 + `DoCombatSpellApply` 一次」推進；Guard 在受擊時降階；`OnFormSwitched/Closed` 清除 |
| 反應（開印、終焉、融斷、放電、地震…） | 傷害法術本身 | `ESSBReactions.Open/End` 照舊，但輸入從「登記表」改為「事件參數 + 目標身上有什麼」 |
| 死亡機制（化灰、亡者歸來、連殺、飲血、血承、蔓延）〔決定 4〕 | 印記與狀態效果帶 No Death Dispel，死時仍在屍體上 | `OnKillEvent` 對屍體 `HasMagicEffectWithKeyword(ESSB_Mark_Divine)` → 化灰，否則 `ESSB_Mark_Darkness` → 亡者歸來；其他死亡節點各看自己的效果。整套擊殺歸屬刪除（第 7 節） |
| 領域、推力、化灰、復生、真傷、破魔、形態層、樹、MCM | 照舊 | 照舊（round 9–16 的修法保留） |

**不再存在的東西**：`ESSBStatus.psc` 全檔；`ESSBController` 的 8 格登記表（`Reg*` 二十餘個陣列）、`PendingStacks/PendingSet/PendingAstral/…`、`BackupInts*/BackupFloats*/BackupValid`、`Swap*`、`StatusHostSpell/EnsureStatus/SwapHosts/FlushPendingState/ClearPendingState`、`AddStack/GetStack/SetStack/AddStackTo/AddAstral/SetFrozen/SetCatalyze/SetDeathCurse/SetStarLock/SetWetLock/SetAirborne`、`DamageActor/DamageElement/SwapFloats`（128 格）；`ESSBState` 的 `BleedSeconds/PoisonSeconds/IntCount/PoisonOffset/TailOffset/NewBleed/NewPoison/NewInts/NewBackup/UpgradeInts`；ESP 的 `ESSB_StatusHostEffect/Spell`、`ESSB_EngagedEffect/Spell`（改嵌進附傷法術）。依賴掃描見第 7 節。

---

## 4. 每種狀態的表示法（對應 alter 2.3）

### 4.1 三種形狀在 ESP 裡長什麼樣

**單階標記**：一顆 MGEF（原型 1 Script 或值修正），KWDA `[ESSB_<Name>, ESSB_Element_X]`，SPEL contact、EFIT duration = N。今天的 `ESSB_Util*`／`ESSB_WindowEffect_*`（`build_v03.py:1584-1596`）就是這個形狀。

**階梯**（名稱 L，k 階）：
- KYWD `ESSB_Ladder_L`（所有階共用）、`ESSB_Cool_L`（成熟計時共用）。
- MGEF `ESSB_L_T{k}`：**原型 0（Value Modifier）、AV = −1、magnitude 0**——照原版 `Oakflesh/Stoneflesh` 的形狀（它們就是用「驅散帶 `MagicArmorSpell` 的效果」互斥，原型 0），所以「Dispel with Keywords 在階梯上生效」不再是假設而是原版用例；KWDA `[ESSB_Ladder_L, ESSB_Tier_L_{k}, ESSB_Element_X]`，旗標 `MGEF_MARKER_FLAGS | 0x100`（Dispel with Keywords）——**驅散清單只放 `ESSB_Ladder_L`**，所以掛第 k 階會移除任何其他階，但不會移除成熟計時；duration = 該階持續秒數；著色器掛在這裡（alter 2.12）。DoT 階則是值修正原型（AV 24，Detrimental、Hostile，同一組 KWDA 與旗標）。
- MGEF `ESSB_L_Cool{k}`：KWDA `[ESSB_Cool_L]`，`MGEF_MARKER_FLAGS`（不驅散任何東西），duration = 成熟秒數。
- SPEL `ESSB_L_Promote{k}` = `[T{k}, Cool{k}]`（升到第 k 階並開始成熟計時）；SPEL `ESSB_L_Refresh{k}` = `[T{k}]`（只重設該階時間，成熟計時不重來）。頂階若有事件（自燃、冰封），SPEL `ESSB_L_Top` 另含事件效果。
- 進入點（每階）：升階段 = 條件「有 T{k−1}」且「沒有 Cool{k−1}」→ 套 `Promote{k}`；刷新段 = 「有 T{k−1}」且「有 Cool{k−1}」→ 套 `Refresh{k−1}`；重擊免等待 = 「有 T{k−1}」且 `IsPowerAttacking == 1` → 套 `Promote{k}`（排在刷新段之前，條件互斥由 `IsPowerAttacking` 保證）。第一階由開印版印記法術一起帶上（alter 2.6 的「開印→溫熱」）。
- 過期：引擎讓 T{k} 到期，什麼都不留。退階（永凍冰封→凍結、熔心自燃→溫熱）由頂階效果的腳本在 `OnEffectFinish` 套一次低階法術。
- 讀取：進入點用 `HasMagicEffect`（214）；腳本用 `Actor.HasMagicEffect(MagicEffect)` / `HasMagicEffectWithKeyword(Keyword)`（`vendor/imports/Actor.psc:316,319`）；要讀強度或剩餘時間用 `PO3_SKSEFunctions.GetActiveMagicEffects(ObjectReference akRef, MagicEffect akMagicEffect)`（`vendor/imports/PO3_SKSEFunctions.psc:609`，回 `ActiveMagicEffect[]`）配 `ActiveMagicEffect.GetMagnitude()`／`GetDuration()`／`GetTimeElapsed()`（`vendor/imports/ActiveMagicEffect.psc:447,362,363`）與 `Dispel()`（`:8`）。PO3 另有 `HasActiveMagicEffect(Actor, MagicEffect)`（`:93`）與 `GetMagicEffectSource(ObjectReference, MagicEffect)`（`:627`）備用。

**DoT 減益**：值修正 MGEF（AV 24 Health、Detrimental、Hostile、**不加** Recover、No Death Dispel 不加），每秒強度在套用前用 `Spell.SetNthEffectMagnitude(int index, float value)`（`vendor/imports/Spell.psc:56`）寫進該階的 SPEL 再 `DoCombatSpellApply`（腳本套用；這是反應路徑，不是命中路徑）；引擎逐秒扣。血潮／催毒結算的「剩餘」＝ `GetMagnitude() × (GetDuration() − GetTimeElapsed())`。

**中毒（單一成長效果）**：`ESSB_PoisonEffect` 是值修正 DoT + `ESSBPoison` 腳本；重套時引擎以新實體取代舊實體（Papyrus 收到舊的 `OnEffectFinish`——腳本用 `Holder.HasMagicEffect(ESSB_PoisonEffect)` 分辨「被重套」與「到期／死亡」）。重套前腳本先 `SetNthEffectMagnitude(0, m')` 與 `SetNthEffectDuration(0, d')`（`vendor/imports/Spell.psc:56,62`）。因為 SPEL 是共用 record，兩個目標在同一幀被重套時會互相覆寫 magnitude——Papyrus 同一實體（Controller）序列化這段呼叫，所以「設值→套用」是原子的；`ESSBPoison` 自己做的擴散／死亡分發也一律呼叫 Controller 的 `PoisonApply(target, m, d)`，不自己碰 SPEL。這是 I4 的一個必要補充：**共用法術的 magnitude 只能由一個實體寫**。

**引信**：單階標記 + 腳本（`ESSBFuse`）：`OnEffectStart` 記下 `GetMagnitude()`（腳本套用前寫好的傷害），`OnEffectFinish` 時若 `!akTarget.IsDead()` 且效果不是被本模組主動驅散（腳本在主動驅散前先呼叫 `MarkCancelled()`）→ `Ctl.ApplyDamage(...)`。星痕 2 秒、死咒 3 秒、浮空 2 秒都是這個形狀。引信升階（星痕 I→II）= 進入點套 `Promote{k}`，舊引信被驅散時 `Cancelled` 由「有更高階存在」判定（`HasMagicEffectWithKeyword(ESSB_Ladder_Astral)` 為真 → 不結算）。

### 4.2 每種機制的對照

| 機制（v0.3） | 新形狀（alter 2.3） | 命中時怎麼讀 | 門檻事件怎麼偵測（不輪詢） | 衰減 | 玩家會感到什麼變了 |
|---|---|---|---|---|---|
| 火 熱度 10 層 → 自燃〔4.6、4.7〕 | 熱度是**你身上**的階梯 3（熔爐 4）：微熱／灼熱 6 s 退一階、成熟 2 s；白熱是 8 s 引信（命中不刷新）且帶**火源披風**（生命 <10% 自動洩壓）；目標只有火印記 | 0x1D 段：法術有 `ESSB_Proc`+`ESSB_Element_Fire` 且**自身**有熱度 T{k}（分頁 0）→ ×1.15／1.35／1.6／1.9 | 過熱：白熱 T3 的引信到期（`ESSBFuse` 型腳本 `OnEffectFinish`，未被洩壓驅散）→ `Ctl.Overheat()`（自燒 10%、對 15 m 內所有帶火印記目標各跑一次火終焉、清熱度）；爆燃（火印記被切掉／融斷）在 `ESSBReactions.EndFire` 讀目標身上其他元素的階（存在測試）與血痕／中毒剩餘（`GetActiveMagicEffects`），算加成後套一次火傷並驅散被消耗的效果 | 引擎（自身階到期由 `ESSBTierDecay` 退一階） | 火變成收尾元素：先用別的元素鋪，再切火養熱度，切走或按 Z 收割；養過頭會燒到自己 |
| 冰 凍結量表 5 = 冰封〔決定 3、6〕 | 階梯 3：寒意／凍結／冰封（1 s／2 s 成熟；冰封 3 s） | 0x1D：冰封 → 冰附傷 ×(1+2%/點)；碎冰由 `OnWeaponHit` 判 `HasMagicEffect(冰封)` → `ApplyTrueDamage(GetBaseActorValue("Health") × 0.2／0.1)` → `DispelSpell(冰封)`（永凍改套凍結） | 冰封本身是 T3；深寒、絕對零度用 `HasMagicEffect(T3)` | 引擎 | 冰封後第一刀 20% 真傷，一次冰封只結算一次 |
| 雷 電荷（你，6／10） | 自身階梯 3（+超載）：12 s、成熟 2 s | 腳本 `HasMagicEffect`；PERK 電盾讀 T3 | 雷神：T3 且無 Cool3 的下一擊 → 腳本放電 | 引擎 | 電荷有「等一下才會升」的節奏；放電四檔 |
| 土 岩甲（你，5／10） | 自身階梯 3（+山岩）：不過期、成熟 2 s；每階是原版石膚型護甲效果 | 腳本；PERK 不動／減傷讀 T{k} | 反震：T3 時被打 | Guard 受擊套低一階（山岳不降） | 石膚→鐵膚→黑檀膚看得見 |
| 風 風勢（你，門檻 4） | 自身單階「起風」5 s、成熟 2 s | 腳本 | 「有起風且無 Cool」的命中 → 風刃 + 驅散 | 引擎 | 每 2～3 秒一段風刃，攻速不影響 |
| 血 血痕 8／12 層，10 s | 〔2026-09-22 還原 v0.3〕層數放血痕效果的 magnitude：開印 2 層、命中 +1，上限 8（深創 12、萬象 15），每層 10 s、命中刷新全部 | 0x1D 不需要；血潮讀 `GetMagnitude×剩餘秒` | — | 引擎 | 放血依 A1b：有每秒執行點就用目標當下生命，否則命中時以當時生命換算 |
| 聖 聖印 5 層〔決定 8〕 | 目標側只剩單階印記（+20% 受聖傷）；玩家側聖佑三階（8 s、成熟 2 s，只有命中帶印記目標才升／刷新） | 0x23 ×3 與 0x1D ×3 段讀自身 `HasMagicEffect(聖佑 T{k})`；升階在 `OnWeaponHit`：`target.HasMagicEffectWithKeyword(ESSB_Mark_Divine)` 為真才套 `Promote` | III 的每擊聖光爆：0x33 段條件「自身有聖佑 III 且目標有神聖印記」→ 套 `ESSB_DivineBurst`（零腳本） | 每階到期時該階 MGEF 的小腳本（`ESSBTierDecay`，`OnEffectFinish` 且未被更高階取代）套低一階 | 打帶印記的目標越久越痛，停手一階一階退 |
| 毒 毒層無上限〔決定 1、2、5〕 | 一顆 DoT，強度與時長隨命中成長（alter 2.7 的公式），催毒 = 同一顆重套 ×2 | 命中時腳本：`PO3_SKSEFunctions.GetActiveMagicEffects(target, ESSB_PoisonEffect)` → `[0].GetMagnitude()/GetDuration()/GetTimeElapsed()` → `SetNthEffectMagnitude/Duration` → `DoCombatSpellApply`（約 6 次原生呼叫，只在毒形態，且在附傷之後、不在關鍵路徑） | 擴散與死亡擴散都在 `ESSBPoison` 腳本（掛在 DoT MGEF 上）：`OnUpdate(2 s)` 傳一劑；`OnEffectFinish` 且 `Holder.IsDead()` → 15 m 掃描全部合格敵人各分一份；無任何成員狀態（份額從自己的 magnitude／duration 算） | 引擎 | 越養越痛、死了全場中毒 |
| 水 浸濕、水壓 5 | 浸濕單階 10 s；水壓階梯 3（8 s、成熟 2 s，只在持有分支且目標浸濕時升階） | 0x1D：水壓 T{k} → ×1.1／×1.3／×1.5 | — | 引擎 | — |
| 暗 詛咒 5／10 | 階梯 3（+IV）：8 s、成熟 2 s；每階是自有抗性弱化 | 0x1D／0x23：頂階 → 受所有傷害 +% | 死咒 = 引信 3 s | 引擎 | — |
| 星 星痕 3／6／9 | 引信階梯 3：各 2 s，命中即升階重計時 | 0x1D（重擊時）：T{k} → +8/16/24% | 到期 = `ESSBFuse.OnEffectFinish` 結算（有更高階存在則不結算） | 引擎 | 上限節點被取代 |
| 戰意（你，5） | 自身階梯 3：5 s | 腳本 | 節奏：命中時「有連段視窗效果」→ 升階 | 引擎 | — |
| 風終焉多段〔決定 9〕 | 無新狀態 | — | `ESSBMark`（風）的 finish 分類為「被切掉」時，取接管元素 e 與 N（讀風樹主線 rank），對目標：`DoCombatSpellApply(HitSpell[e])` N−1 次（第 2 次起先把 magnitude ×0.5 寫進一顆「回聲」副本法術 `ESSB_Hit_<X>_Echo`，避免改壞主法術）、`Promote(e 的階梯)` N−1 次（免等待）、雷則每次 `RandomInt(1,25)` 取 best-of-電荷階 寫進 Echo 再套；中毒 +N−1 劑；聖佑 +N−1 階 | 一次終焉 2N 次原生呼叫，不在命中關鍵路徑 | 切換那一刀像連打 N 下 |
| 同調（你，計數 5／15／30） | 〔2026-09-22 還原 v0.3〕計數放同調效果的 magnitude：命中 +1，門檻 5／15／30 換段（現有 `ESSB_SyncStage` GLOB 仍由升階時寫入，既有 167 段條件不改） | 升段 = 命中時 magnitude 到門檻 → 套對應段效果 | 切換／關閉時 `DispelSpell`／清零 | alter 第 1 條 |
| 冰盾／水鏡／聖盾（你，5／3／5） | 自身階梯 3：8 s、成熟 1 s | PERK 0x24／0x29 讀 T{k} | — | Guard 受擊套低一階 | — |
| 裂痕、失衡、破魔印、星鎖、浮空、已交戰、最後一擊 | 單階標記（既有做法） | 214／699 | 浮空 = 引信 | 引擎 | — |

### 4.3 兩半怎麼合成一個架構

- 附傷法術版本數維持小（普攻／重擊／風潛行 2 筆／血四區間 6 筆）；**所有「目標帶 X 時本模組傷害 ×N」寫成 0x1D「Mod Spell Magnitude」段**：分頁 1（法術）`EPMagic_SpellHasKeyword(693)` 讀 `ESSB_Proc` 或 `ESSB_Element_X`，分頁 2（目標）`HasMagicEffect(214)` 讀階，數值是倍率。原版 `AugmentedFlames60` 在 0x1D 分頁 1 用 693、Ordinator `ORD_DesNPC_FirePerks_Perk_60_WasAugmentedFlames` 在 0x1D 分頁 2 用 214（high，位元組實測）。這樣灼熱、聖印、水壓、星痕弱點、詛咒頂階、星鎖、星域、火域、御風、空中追擊、電蝕全部零腳本，也不再需要第一版計畫裡的「腳本補刀」。**未驗證（medium）**：0x1D 是否作用在進入點套用的法術上；若實機不成立，退回「每階一個法術版本」（生成器多吐 30 筆 SPEL，進入點多 30 段），語意不變。
- 「目標帶 X 時你的**武器**傷害 ×N」（御風、空中追擊）寫成 0x23「Mod Attack Damage」段，分頁 2 讀目標的階（Ordinator 在 0x23 分頁 2 用 214 共 10 段，high）。這反轉了 `實作紀錄.md:865-870` 的決定 61。
- 開印那一擊 ×1.5（深印、烈火點燃等）寫成 0x1D 段：分頁 2 `HasMagicEffectKeyword(699, ESSB_Mark_X) == 0`——印記由同一次命中的另一段套上，所以下一擊看到的印記是真的，不會像腳本晚到那樣連續吃到開印倍率。**同一次命中內多段的評估順序**（附傷段先看「沒有印記」，印記段再套上）需要實機確認（low）；若順序相反，開印倍率改由開印版印記 MGEF 的腳本補一刀。
- 你身上的階梯由腳本推進，但 PERK 條件直接讀它們（既有的 `ESSB_SyncStage`、`ESSB_Charge` 等 GLOB 鏡射可以留著，升階時寫一次；round 16 的九個防護視窗已經是「HasMagicEffect 讀原生限時效果」的做法，`build_v03.py:773-775`）。若實機證明「Apply Combat Hit Spell」也能對施法者套用 Self 傳遞的法術（原版 `TGNightingaleShadowPerk` 用 0x45「Apply Sneaking Spell」對自己套用；0x33 沒有原版用例，low），這些也搬到引擎。

### 4.6 火的重設計：為什麼採「收割者」（使用者提問：別的遊戲的火都在做什麼）

**一、常見的火元素原型**（依機制歸類，不逐一點名遊戲）：

| 原型 | 玩起來的感覺 | 要玩家做什麼 |
|---|---|---|
| 燃燒 DoT（打中後慢慢燒） | 掛上就不管，比的是覆蓋率 | 維持 uptime，沒有操作 |
| 蔓延／傳染（火從一個燒到一群、燒地形） | 位置感，把人趕進火裡 | 走位、選擇引燃點 |
| 疊層後自耗引爆（疊到 N 層炸一次） | 節奏是「打、打、打、炸」 | 數層、等炸，操作單薄 |
| 熔甲／削抗（火軟化目標） | 先燒再打，火是前菜 | 順序：先火後主力 |
| 恐慌／驅散（著火的人亂跑） | 控場，敵人散開 | 利用混亂脫戰或補刀 |
| 吃屍體／吃地形（燒屍體、燒油、燒草） | 環境互動，變化最多 | 讀場地 |
| 反應觸媒（火與別的元素反應：蒸發、融化、超載） | 組合技，火是收尾鍵 | 規劃順序、記住誰身上有什麼 |
| 熱度自身資源＋過熱風險（越打越燙、燙到會反噬、要洩壓） | 節奏管理，有張力 | 判斷何時洩壓 |
| 燃料／附魔（火強化下一招或武器） | 火是放大器 | 先點火再出大招 |
| 依目標當前／已損生命的火傷 | 對高血或殘血特化 | 挑目標 |
| 死亡爆炸／連鎖（燒死的人炸開） | 清雜兵爽感 | 先殺一個 |
| 地面火域（留火區） | 區域拒止 | 佈陣、拉扯 |

**二、已被本模組其他元素占走的**：蔓延與死亡連鎖（毒）、削抗（黑暗）、破甲（大地）、恐慌（黑暗的恐懼／瘋狂）、依生命比例（冰的碎冰、血的放血）、持續 DoT（血、毒；且 v0.3 明定火沒有持續傷）、成長型自身增益（神聖）、放大下一次終焉／開場（水、星）、次數（風）、地面火域（所有元素的融斷領域都有）、燒屍體（神聖的化灰）。剩下沒被占走、又符合「連打累積、自動引爆」的只有三個：**疊層自耗引爆**（現況，使用者嫌無聊）、**反應觸媒**、**熱度自身資源＋過熱**。

**三、候選**：
- **A（指揮官提案，採用）：熱度在玩家身上、終焉消耗目標的其他狀態。** 命中養熱度（自身階梯），熱度放大火附傷與爆燃；切換或融斷＝洩壓，火印記的終焉把目標身上別的元素的狀態吃掉換成火傷；白熱不洩壓就過熱：自燒並讓所有帶火印記的目標自動引爆。玩家要做的事：**決定何時洩壓**，以及**先用別的元素鋪、最後切火收**。與核心循環的接法最直接：風給次數、水給強度、星給開場、火吃掉全部。引擎成本最低：目標側不需要任何階梯（只有印記），自身階梯與其他資源同一套，0x1D 段讀自身效果即可；消耗換算只在終焉時跑一次腳本。原本的缺點「火單獨用時沒東西可吃」由白熱火源解決（4.7）。
- **B：火域為本體（地面火）。** 開印與終焉在目標腳下留 3 秒燃燒地帶，站在裡面的敵人受火傷並被掛火印記；引擎有原生 Hazard（原版火焰之牆的做法），零腳本。玩家要做的事：走位、把敵人拉進火裡（風的拉近正好配合）。缺點：與所有元素的融斷領域重疊、室內走位空間小、Hazard 對必要角色與友軍的判定要實測；也偏離「連打累積」。適合當火域節點的強化，不適合當本體。
- **C：疊層引爆（現況）加手動引爆。** 把「自動炸」改成「你決定何時炸」——但那就是 A 的一半，且熱度留在目標上要多 3 顆階 MGEF 與 6 段進入點。

**選 A**：它是唯一同時滿足「有自己的操作」「接上鋪場→收割的核心節奏」「不與任何元素撞」「引擎最便宜」的方案；v0.3 的三個識別點都保住：連打累積（熱度）、自動引爆（過熱時全場火印記引爆）、沒有持續傷。代價是火從「對單體越打越痛」變成「對場面收尾」；單獨用火時由白熱火源鋪印記（4.7），不再平。

### 4.7 白熱火源：用引擎的披風原型（使用者追加）

**原版怎麼做（high，`Skyrim.esm` 位元組）**：`FireCloakFFSelf` 是原型 **35（Cloak）**的 MGEF，DATA 位移 8 的「關聯物件」指向 `FlameCloakDmg`（SPEL，casting 2 concentration、delivery 2 aimed）；披風法術 `flameCloak` 的 EFIT magnitude 10 = 半徑（原版單位約 10 呎 ≈ 3 公尺）、duration 60。引擎每秒對半徑內的角色施放關聯法術，不經 Papyrus。**目標過濾在關聯法術的傷害 MGEF 上**：`FireDamageConcAimedCloak` 帶 MGEF 條件 `IsHostileToActor`（719）`== 1`——這就是原版火焰披風不燒同伴的原因；披風本身不做過濾。

**本模組的做法**：
- 白熱 T3 的自身 SPEL = `[熱度 T3 標記（8 s 引信，帶 ESSBFuse 型腳本）, ESSB_HeatCloakEffect]`；披風 MGEF 的 `hit_shader` 掛全身火焰著色器（已定的唯一身體特效例外，`settings.json` 選擇器 `fx_heat_body`，預設 Vulcano `DAR_MoltenFXShader`，缺素材退回 Phenderix `ZZShader_FireForm`）；`ESSB_HeatCloakEffect` = 原型 35、`assoc = ESSB_HeatCloakDmg`、EFIT magnitude = 10（3 公尺；熔燒版 15），duration 同 T3。T3 被洩壓驅散時披風一起消失，所以火源只在形態開啟且白熱時存在。
- `ESSB_HeatCloakDmg`（SPEL，casting 2／delivery 2）= `[ESSB_HeatCloakDamage, ESSB_MarkCloak_Fire]`。傷害 MGEF：值修正 AV 24、`skill=20`、`resist=41`、KWDA `[ESSB_Element_Fire, MagicDamageFire]`（**不帶 `ESSB_Proc`**，所以 0x1D 的附傷倍率不會再乘上去），magnitude = `B_max × 0.5 × G(L)`（由 `RefreshProcMagnitudes` 一起寫）；MGEF 條件：`IsHostileToActor(719) == 1`（照抄原版）+ `GetPlayerTeammate(453) == 0` + `IsCommandedActor(700) == 0` + `GetDead(46) == 0`。**引擎過濾能做到的**：敵對者、非同伴、非受命者；**做不到的**：2.9 的「敵對陣營但尚未察覺」不會被燒（`IsHostileToActor` 為假）——這是安全側（在城裡白熱不會燒路人），列為刻意偏離；「已交戰」的中立者一被打就會敵對，自然涵蓋。同伴被燒的那次事故（使用者提到）在這裡由 453／700 兩條 MGEF 條件擋掉；再保險一層：`ESSB_HeatCloakDamage` 加 No Hit Event（0x10），不觸發任何人的受擊事件。
- `ESSB_MarkCloak_Fire`：與火印記同 KWDA（`ESSB_Mark_Fire, ESSB_MarkAny, ESSB_Element_Fire`）、同驅散清單、8 s，帶 `ESSBMark`（`Mode = 2`：不觸發開印反應，只負責終焉分類與被切掉時的接管），MGEF 條件 `HasMagicEffectKeyword(699, ESSB_Mark_Fire) == 0`——目標已有火印記時披風不重套，所以每個目標最多每 8 秒一次 `OnEffectStart`，沒有每秒的 Papyrus。
- 過熱改為引信到期而不是「頂階成熟後再命中」：這樣白熱的 8 秒是真的可以「騎」的（一直打人也不會提早過熱）；命中不刷新 T3（刷新段的條件排除 T3），洩壓 = `DispelSpell(T3)`（`ESSBFuse` 看到被驅散就不觸發過熱）。
- 成本：披風本身是引擎；每個被燒的目標每 8 秒一次印記腳本事件；`RefreshProcMagnitudes` 多寫 1 個 magnitude。
- **公式（已定）**：你的代價 = 最大生命 × 0.5%／秒；敵人每秒 = `(基礎燃燒 + 代價 × N) × M_mod(火附傷純百分比)`，基礎燃燒 = `B_max × 0.25 × G(L_火)`（使用者加碼的「從第一點就存在的基礎值」；原本的下限併進它，所以沒有 max()），N 從 ×2 由火樹買到 ×8.5（alter 5.3 有階梯與三期數字：4.65／20.2／109 每秒每敵，全部高於 3.2／12.6／60 的硬性下限）。引擎側只是一個 magnitude：`RefreshProcMagnitudes` 在升到白熱、生命上限改變、火樹投點時算一次寫進 `ESSB_HeatCloakDmg`，沒有每秒腳本。
- **自動洩壓（已定）**：`ESSBFormRules.OnUpdate` 每秒扣代價前先看 `Holder.GetActorValuePercentage("Health") < 0.10` → `Ctl.VentHeat()`（= 洩壓：對帶火印記目標各跑一次火終焉照熱度算、`DispelSpell(T3/T4)`、不付過熱代價、熱度依「洩壓」節點留階）。過熱的引信到期回呼（`ESSBFuse` on T3）先檢查「T3 是否已被洩壓驅散」——被驅散就不觸發；所以順序是：低血→洩壓先發生→引信被驅散→過熱不會再砍一刀。
- **你的代價不是傷害，是維持費（已定）**：走 `ESSBController.PayBloodCost` 同一條路（`ESSBController.psc:3246-3266`：`GetActorValueMax × 百分比` → 夾到 `current − 1` → `DamageActorValue("Health")`），改成通用的 `PayHealthCost(percent)`，由 `ESSBFormRules.OnUpdate`（每秒，`ESSBFormRules.psc:100` 旁邊）在 `Holder.HasMagicEffect(HeatT3 或 T4)` 時呼叫。`DamageActorValue` 不是命中：不發 `OnHit`／PO3 `OnHitEx`（`ESSBGuard` 的反震、殘影、影身、靜電、毒皮、冰盾／水鏡／岩甲降階都不會動）、不觸發神佑（`RefreshDivineProtection` 只看 ≤0，代價永遠留 1 點）、不進戰鬥、不解除潛行、不吃火抗、不被任何「受傷 ×N」進入點改變。過熱的 10% 也走 `PayHealthCost(0.10)`（已定；原 `OverheatSelfSpell` 火傷法術停用）。留 1 點是代價路徑的通則；火源本身在生命 <10% 時已自動洩壓（上一條）。
- **敵方傷害的 magnitude 由誰寫**：`RefreshProcMagnitudes` 在熱度升到白熱／熔燒時與生命上限改變時（`GetActorValueMax` 在 `RefreshRuntimeValues` 讀一次即可，等級提升時會跑到）寫 `ESSB_HeatCloakDmg` 的 magnitude = `(B_max × 0.25 × G + maxHP × 0.005 × N) × M_mod`；N 由火樹 rank 算。披風關聯法術的 MGEF 帶 `ESSB_Element_Fire` 與 `MagicDamageFire`，所以吃火抗與 Ordinator／裝備的火系加成，和附傷一樣；掛 `ESSB_MarkCloak_Fire`，所以算本模組的火印記、死亡機制看得到、過熱與爆燃都吃得到。
- 最壞疊加：火源與血形態維持費不可能同時（同一時間一個形態）；火形態內一輪 = 0.5%×8～18 秒 + 過熱 10% ≈ 14～19% 最大生命，全部留 1 點，不會直接致死；魔力維持費是另一個資源。
- 半徑 3 公尺（熔燒 4.5 公尺）；白熱引信 8 秒（添薪 12 秒）。
- 未驗證（medium）：披風 magnitude 的單位（原版 10 對應「近戰範圍」，實機量一次）；`IsHostileToActor` 參數 0 在 MGEF 條件裡的語意（原版就是這樣寫，照抄即可）；披風關聯法術是否會被 0x1D／0x23 段影響（不帶 `ESSB_Proc` 就不會）。

### 4.10 探針結果：一刀只套一個進入點法術——第 2 期改成「一段選一顆多效果法術」

**實機結果（2026-09-22，`.codex/smoke8-probe-results-Papyrus.0.log`、`.codex/smoke9-probe3-Papyrus.0.log` 的 `[ESSB-PROBE]` 行，主模組停用、只載 `build/fix18-probe-package/`，校準 k=0.95）**：
1. 0x1D「Mod Spell Magnitude」對 entry 51 套用的法術**有效**，乾淨翻倍（19／0.95 = 20）→ `tier_multiplier_mode = entry`（第 11 節第 4 題關閉）。
2. 同一 PERK 兩段 entry 51 同時成立（A 優先度 200、B 199）→ 只套 B。
3. 兩個不同 PERK 各一段 entry 51 同時成立：A200/B199 → 只套 B；A199/B200（perk 順序與 FormID 不變）→ 只套 A，三刀一致。
**結論：所有 PERK 的 entry 51 合起來，一次命中只套一顆法術，勝者是優先度位元組（PRKE 第 3 位元組）最小的那一段，與 perk 先後、FormID 無關；同優先度的勝負未測。**

**（4.11 之後的定位：本節的效果層條件是 DLL 選錯時的雙重保險，不再是命中路徑；一刀一法術的限制對 DLL 不適用。）** 原第 2 期表示法：每一刀恰好一段 entry 51 成立（玩家側條件：形態、元素、重擊、潛行、弓弩、血位區間——第 1 期已是互斥的 74 段），該段套**一顆多效果法術**，法術裡每個效果各自帶**效果層條件**（SPEL 的 EFID/EFIT 後接 CTDA，引擎對同一法術的每個效果分別評估；條件的主體是被套用的目標）。目標側的判斷全部搬到效果層：

| 效果（同一顆 `ESSB_Hit_<X>_<變體>` 法術裡） | 效果層條件（主體 = 目標） |
|---|---|
| 附傷 MGEF（magnitude 由 `RefreshProcMagnitudes` 寫） | 無 |
| 已交戰標記（30 s） | 無 |
| 開印版印記 `ESSB_MarkOpen_X` | `HasMagicEffectKeyword(ESSB_Mark_X) == 0` |
| 刷新版印記 `ESSB_MarkRefresh_X` | `HasMagicEffectKeyword(ESSB_Mark_X) == 1` |
| 階梯升階 `T{k}`＋`Cool{k}`（k = 2..n） | `HasMagicEffect(T{k−1}) == 1` 且 `HasMagicEffect(Cool{k−1}) == 0`；重擊變體的法術省略 Cool 條件（免等待） |
| 階梯刷新 `T{k−1}`（不含 Cool） | `HasMagicEffect(T{k−1}) == 1` 且 `HasMagicEffect(Cool{k−1}) == 1` |
| 頂階事件（冰封本身、白熱不適用——熱度在玩家身上） | 同升階條件 |
| 中毒（第 2 期仍是腳本重套，不放進法術） | — |

**依據**：這正是 Ordinator 自己的做法——它的 entry 51 目標法術裡 `ORD_One_RiseKinsmen_Spell_DentingBlows_90`（5 個效果、7 條效果層條件）、`ORD_One_Shieldbiter_Spell_BleedLikeALamb_60`（3 效果、4 條件）、`ORD_One_BiteMarks_30_PowerAttackSide`（8 效果、3 條件）等 12 顆都是「一顆法術、多效果、效果各自條件」（本機 ESP 位元組實測，high）；原版 `flameCloak` 的效果層條件（289、72）與本模組現行 `ESSB_FormAbility_<X>` 的同調條件（`build_v03.py:1414-1420`）是同一機制。0x1D 的階倍率、0x23 的武器傷害放大是**別的進入點**，不受「一刀一法術」限制（原版 Augmented Flames 與 Destruction Mastery 本來就疊乘）。

**記錄量**：MGEF 不變；SPEL 數不變（每元素每變體一顆，約 40 顆），每顆從 1～2 個效果長到 6～12 個效果；entry 51 段數從約 130（附傷 74 + 印記 22 + 升階 ~44）**降到 74**；0x1D／0x23 段照舊。**要換寫法的機制**：印記開印／刷新（效果層）、所有目標階梯的升階／刷新／頂階（效果層）、開印 ×1.5（0x1D 段的分頁 2 條件 `HasMagicEffectKeyword(ESSB_Mark_X) == 0`，magnitude 在效果套上之前算，所以開印那一刀吃到、下一刀不吃）、雷五檔（第 1 期已是恰好一段成立：五段依優先度 R5→R1 遞增，每段各自 `GetRandomPercent`，最小優先度且條件成立者勝＝鏈式，不必改）、風多段觸發的 `WindEcho` 改為 `DoCombatSpellApply` 這顆多效果法術 N−1 次（效果層條件對腳本套用同樣生效）。**不用改的**：自身階梯（腳本或第 3 期 Self 法術）、中毒重套、碎冰、白熱火源（披風是自己的機制）。

**跨模組的取捨（要使用者決定，見 alter 2.13 與本節末）**：原版 Hack and Slash／Limbsplitter（斧流血，優先度 3）、Bullseye／Paralyzing Strike／Warmaster／TrickShot（優先度 0）、Ordinator 約 129 段（優先度 50～209，本機位元組實測）都用 entry 51。開形態時我們的附傷幾乎每刀成立，所以：
- **甲：取最小優先度（0）→ 開形態時我們穩贏。** 玩家感覺：形態開著時 Ordinator 的武器命中天賦（流血、骨折、釘射等）不會觸發；關形態（無元素樹）時全部照舊。成本：零。風險：玩家投在那些天賦的點在形態內看不到效果。同優先度平手：使用者裝 Ordinator，Ordinator 最小 50，不會平手；只有沒裝 Ordinator 的原版天賦樹（Bullseye 等 0）會平手，平手規則未測——若使用者要顧原版樹，加一題探針（1-10）。
- **乙：取最大優先度（255）→ 讓給對方。** 對方條件成立的那一刀我們整顆法術不套：附傷沒有、印記沒掛、階梯不升。Ordinator 的流血類多半是「每刀成立」（只看武器 keyword），所以斧頭流在形態內幾乎每刀都掉附傷——等於沒有這個模組。不建議。
- **丙：相容層（我們的法術裡吸收對方的效果）。** 只能做原版那幾顆（`PerkBleedingSword*`、`PerkBullseyeParalyze` 等，masters 只有 Skyrim.esm）；Ordinator 的 129 段不能引用（要加 master），而且 Papyrus／PO3 沒有列舉「這一刀被壓掉的其他段」的 API。成本中、只救原版、Ordinator 使用者沒有得到任何東西。不建議作為主方案；可當之後的選配。
- **丁：SKSE 插件解除「一刀一法術」。** **未查證**（無網路）：要查 Scrambled Bugs、po3 Tweaks、Bug Fixes SSE 的修正清單有沒有「Apply Combat Hit Spell 只套一顆」這一條；若沒有，就是自寫插件（本專案範圍外）。不能憑記憶斷言存在。
- **戊：附傷改走別的觸發。** entry 51 以外沒有「命中即套法術」的引擎路徑（0x43 是揮擊不是命中、0x34 是盾擊）；回到 PO3 `OnWeaponHit` 腳本就是回到第 1 期之前的延遲。不建議。
**建議甲**，理由：形態內本模組本來就是「武器命中效果層」，無元素樹的存在就是讓原版／Ordinator 的武器天賦有舞台；成本零、無平手風險（有 Ordinator 時）。這是使用者的決定。

### 4.11 第四題結果、相容性清查，與三條命中路徑的並排評估（使用者偏好 SKSE 原生插件）

**第四題（同優先度平手）**：兩個不同 PERK 各一段 entry 51、優先度都是 0——變體 1（A 編號小、先加）A 贏；變體 2（A 編號大、先加）A 贏；變體 3（A 編號小、後加）B 贏。**平手時先加到角色身上的 perk 贏，FormID 無關**（log 待指揮官補檔）。對甲案的意義：`ESSB_P_HitProc` 在 `Setup` 就 `AddPerk`，比後來分發的 0 優先度天賦早；但 Darenii「X 之軀」（施法→MGEF perk to apply→entry 51 優先度 0）與 Stealth Kill Detection Fix（潛行偷襲，優先度 0）若比我們早在角色身上，那一刀會輸——甲案風險小但可列舉（`build/entry51-compat-audit.md` 逐項 a/b/c/d）。

**新發現的第二條引擎路**：Arcanum「神聖鋒刃」、Colorful Magic「神聖附魔」用 MGEF 原型 39（Enhance Weapon）把臨時附魔掛到手上武器，走武器附魔管線，不佔 entry 51。

**三條路並排**（丙＝使用者偏好）：

| 軸 | 甲：entry 51 取優先度 0 | 乙：Enhance Weapon（原型 39 臨時附魔） | 丙：SKSE 原生命中事件（DLL） |
|---|---|---|---|
| 手感延遲 | 引擎同幀 | 引擎同幀（附魔管線） | 引擎同幀（C++ 接事件，不排 Papyrus） |
| 與其他模組共存 | 一刀一法術：贏了對方就沒；平手看誰先加 perk | 不佔 entry 51；**與武器既有附魔的關係未知**（覆蓋？並存？消耗充能？） | 不佔 entry 51；DLL 自己套法術，不動任何天賦 |
| 依目標狀態／自身階決定效果 | 玩家側靠段條件、目標側靠效果層條件（4.10）；能做，但每個判斷都是一顆效果加一組 CTDA | 附魔效果也能帶效果層條件；magnitude 是附魔記錄的固定值，換元素＝換附魔 | **最自由**：C++ 直接讀目標效果列表與玩家的階，決定套哪幾顆、多少強度，不受一刀一法術限制 |
| 第 2 期變簡單／變難 | 已寫好（4.10）；難在效果層條件的組合爆炸 | 重做整個附傷家族成 ENCH；拳腳沒有武器→沒附傷；雙持左手另一顆 | 變簡單：印記／升階／開印倍率不必塞成效果層條件；ESP 只剩法術與效果的定義 |
| 開發與維護成本 | 零 | 中（新家族＋大量實機未知） | 高：C++ 專案、CommonLib 相依、建置鏈、遊戲版本變動要重建；程式量小（一個事件 sink、一張表） |
| 出錯後果 | 最壞少一刀附傷 | 最壞附魔互吃或武器狀態異常 | **DLL 錯＝遊戲崩潰**；靠版本檢查＋自我停用封住（停用時無附傷，無第二條路） |
| 執行期 | 無 | 無 | 只支援 SE 1.5.97（使用者永遠不升級；SKSE 2.0.20、Address Library `version-1-5-97-0.bin` 本機已有）——不是代價 |

**裁決（使用者 2026-09-22：「單純走丙；給網路」）**：只走 SKSE 原生插件，**不保留甲（entry 51）為退路**；實作代理可連網，限下載建置相依與查閱其文件／原始碼。乙不做。

#### 丙的架構

**DLL 負責的（且只負責這些）**
1. **接命中**：以 CommonLib 的事件 sink 接引擎的命中事件（`TESHitEvent`：目標、攻擊者、來源武器、投射物、旗標——PO3 `OnWeaponHit` 的來源就是它，但我們在 C++ 端同幀處理，不轉送 Papyrus）。**不做 trampoline hook**：事件 sink 只依賴 CommonLib 的穩定 API，不依賴任何函式位址；若之後證明事件時機（傷害之後）不夠用才考慮 hook（位址待查證，見下表）。
2. **判斷**：攻擊者是玩家；來源是武器或拳腳（型別 0～7、9，排除法杖）；旗標（重擊、盾擊、格擋、潛行）；目標是 Actor、活著、非同伴／受命；本模組 GLOB `ESSB_Enabled`、`ESSB_FormActive`、`ESSB_CurrentElement`（直接讀 `TESGlobal` 值，零成本）。
3. **決定與套用**：依元素、變體、玩家血位（血）、目標身上的效果與玩家身上的階，選一組法術：附傷（含已交戰）、開印版或刷新版印記、升階或刷新、頂階事件；每顆用「以玩家為施法者的即時施放」套到目標（與 `DoCombatSpellApply` 同一條路，所以 Ordinator 天賦、抗性、0x1D 倍率照舊；不發 `OnSpellCast`——換了呼叫端，探針卡 N-5 再驗一次）。一刀可套多顆，沒有一刀一法術的限制；**效果層條件仍留在法術裡**當第二道保險（DLL 判錯也不會雙掛）。
4. **不做的**：不算傷害（magnitude 仍由 Papyrus `RefreshProcMagnitudes` 寫進法術，DLL 只套）、不碰 Papyrus 佇列、不寫存檔、不 hook 任何函式。

**ESP／Papyrus 保留的**：MCM、技能樹（CSF）、形態層（`ESSBInput`、`SwitchForm`、能力）、法術強度重寫、反應（`ESSBMark`／`ESSBEmber`／`ESSBFuse`／`ESSBPoison`）、自身階梯推進、融斷、領域、擊殺結算、除錯 log、所有記錄定義。**`ESSB_P_HitProc` 的 entry 51 附傷段在第 2N 期整段移除**（0x1D／0x23 段與其他既有進入點不動）；本模組不再有任何 entry 51 段，也就不再與任何模組搶那個位置。

**溝通**
- `ESSB_NativeHit`（新 GLOB）：只表示「DLL 正在處理命中」——DLL 載入且版本檢查通過時寫 1，例外、版本不符或 MCM 關閉時寫 0。**0 = 本模組沒有命中附傷、印記與升階**（使用者已知並接受）；沒有第二條路徑。
- 記錄查找：建置產生 `SKSE/Plugins/ElementsSpellblade/manifest.json`（每顆法術與效果的本地 FormID、元素索引、變體），DLL 啟動時以本地 FormID + 插件名解析一次；不用 EditorID（執行期沒有）。
- Papyrus 原生函式（`ESSBNative.psc`，DLL 註冊）：`Bool IsNativeHitActive()`、`String NativeVersion()`、`Function SetNativeHit(Bool)`（MCM 用）。
- **DLL 的 log〔定案〕**：檔案 `Documents\My Games\Skyrim Special Edition\SKSE\ElementsSpellblade.log`（SKSE 插件慣用的 log 目錄，與 `skse64.log` 同層），啟動時覆寫；除錯等級由 DLL 每次命中前讀 `ESSB_DebugLevel` GLOB，格式與 Papyrus 一致：`[ESSB][hit][L2] <目標FormID> element=<n> weapon=<型別> power=<0/1> sneak=<0/1> spells=<套了幾顆>`；L1 固定寫載入結果（`version 1.5.97 ok, native hit ON` 或停用原因）；Papyrus 端不再有每擊 log。

**過渡**：第 1 期（entry 51）已部署；第 2N 期第一切片以 DLL 取代 `ESSB_P_HitProc` 的附傷段——同一套法術、同一張選擇表，行為與 round 18 的 `HITPROC` 真值表逐格相同；附傷段在同一切片移除。回退手段是還原上一版套件（round 18），不是開關。

**第 2 期計畫的改寫**：印記與升階由 DLL 依目標效果選法術；4.10 的效果層條件表**降級為雙重保險**（每顆法術的效果仍帶目標側條件，DLL 選錯也不會同一刀掛兩個印記或跳兩階；生成器照舊產生）。**不變的**：所有 MGEF／SPEL 定義、階梯與餘燼機制、中毒重套、碎冰、風多段、聖佑、火源、自身階梯、擊殺看印記、0x1D／0x23 段、`RefreshProcMagnitudes`。

#### 無法從本機檔案確認、需要查證的（派 Astra 前先問使用者網路權限）

| 項目 | 要查什麼 | 去哪裡查 |
|---|---|---|
| CommonLibSSE 的分支 | 單執行期即可（不必 NG 的多執行期）：powerof3 的 CommonLibSSE 或 NG 鎖 1.5.97；需要的 CMake preset 與 `SKSEPlugin_Query` 舊式匯出 | 各自 GitHub README、範例插件 |
| 命中事件 | `RE::TESHitEvent` 的欄位名（target／cause／source／projectile／flags 的旗標值）與 `RE::ScriptEventSourceHolder::GetSingleton()->AddEventSink` 的用法 | CommonLib 標頭 `RE/T/TESHitEvent.h`、`RE/S/ScriptEventSourceHolder.h` |
| 即時施放 | `RE::Actor::GetMagicCaster(RE::MagicSystem::CastingSource::kInstant)` 與 `RE::MagicCaster::CastSpellImmediate(...)` 的參數順序——SKSE `DoCombatSpellApply` 的實作就是它，但本機 `vendor/skse64.zip` 沒有這支函式，簽名要查 | CommonLib `RE/M/MagicCaster.h`、SKSE64 `PapyrusActor.cpp` |
| 目標效果查詢 | `RE::MagicTarget::HasMagicEffect(EffectSetting*)`、keyword 版本的實際名稱 | CommonLib `RE/M/MagicTarget.h`、`RE/A/Actor.h` |
| GLOB 與記錄查找 | `RE::TESGlobal::value`、`RE::TESDataHandler::GetSingleton()->LookupForm<T>(localID, modName)` | CommonLib 標頭 |
| Papyrus 原生註冊 | `SKSE::GetPapyrusInterface()->Register(fn)` 與 `RE::BSScript::IVirtualMachine::RegisterFunction` 的簽名 | SKSE／CommonLib 範例 |
| Address Library | 上述 API 是否全部經 vtable 或已解析的 `REL::ID`；1.5.97 對應 `version-1-5-97-0.bin`（本機已有） | CommonLib 內部 `REL::ID` 使用處 |
| 若之後要 hook | 命中處理函式的 REL::ID（社群插件 Precision／Valhalla Combat／MaxsuPoise 的「OnMeleeHit」位址）——**本檔不寫任何 ID 當事實** | 各插件的公開原始碼 |
| 建置相依（要網路） | CommonLibSSE(-NG) 原始碼、vcpkg 或 CMake FetchContent、spdlog、fmt、binary_io、rsm-binary-io、xbyak（不 hook 可省）；MSVC 17.14 與 CMake 本機已有 | vcpkg registry／各 repo |
| SKSE 版本 | 本機 SKSE 版本（應為 2.0.20）與載入器要求的舊式 `SKSEPlugin_Query` 匯出 | `SkyrimSE/skse64_loader.exe` 版本、SKSE 官網 |
| 施法事件（2026-09-23 新增，供反咒使用） | 是否存在可接的「敵人施法」事件 sink（等效 `TESSpellCastEvent`），能否取得施法者、消耗魔力、施放的法術；若不存在，反咒需要另尋替代或保留現況的動畫事件監聽 | CommonLib `RE/T/TESSpellCastEvent.h`（若有）；否則對照現況 `ESSBCounter.psc` 的 `MRh_SpellFire_Event`／`MLh_SpellFire_Event` 做法 |
| 命中時讀取目標施法狀態（2026-09-23 新增，供雷滿格法術麻痺、斷咒使用） | C++ 端能否在命中 sink 內即時讀出目標是否正在施法（旗標或等效狀態） | CommonLib `RE/A/Actor.h`；對照現況 Papyrus `PO3_SKSEFunctions.IsCasting` |
| 中斷施法（2026-09-23 新增，供雷滿格法術麻痺、斷咒使用） | 有沒有安全的原生 API 可以讓「正在詠唱」的那一發法術失效／被打斷，而不需要改寫引擎程式碼（專案原則不做 hook 引擎函式） | CommonLib `RE/M/MagicCaster.h` 等；若查無安全 API，這兩個效果需要改寫實作方式，待查證結果回頭修正設計 |
| 效果套用事件（2026-09-23 新增，供水浸濕滿層沖刷、N3 毒的「+劑」使用） | 能否接引擎「效果套用」（`OnEffectApply`／等效於效果移除事件的另一半）事件 sink，判斷某效果是否「施法得來、有持續時間、屬增益」 | CommonLib 事件 sink 相關標頭；與上方「過期／死亡回呼走效果移除事件」同一組待查證項 |

#### 風險與保險
1. **崩潰**：sink 內只做指標判空、旗標判斷、GLOB 讀取、查表與即時施放；不配置記憶體、不呼叫 Papyrus、不遞迴（來源是法術的命中事件直接忽略；附傷 MGEF 已帶 No Hit Event）。整個 handler 以 SEH 包住（CommonLib 是否提供包裝待查證），任何例外→記 log、`ESSB_NativeHit` 寫 0、之後不再處理。
2. **版本不符／例外**：載入時比對執行期版本是否 1.5.97 且 Address Library 檔存在；不符或 sink 內任何例外→記 log、不再處理、`ESSB_NativeHit` 寫 0。遊戲照常，但**本模組沒有元素附傷**（使用者已接受）；回退手段是還原上一版套件。
3. **MCM 一鍵停用**：`SetNativeHit(False)` → DLL 停止處理、GLOB 0；不需重載；同樣是「無附傷」，不是退回別條路。
4. **雙套保險**：法術效果層條件保留（4.10），DLL 判錯也不會同一刀掛兩個印記或跳兩階。
5. **驗收**：探針卡 2N（10.2）。

**開發量估計**：C++ 約 400～600 行（sink、manifest 載入、選法術表、GLOB、原生函式註冊、log）加一個 CMake 專案；第一次建置鏈設定是主要成本。

### 4.9 印記的終焉分類不依賴事件順序：「餘燼標記」

第 2 期原本讓舊印記的 `OnEffectFinish` 用「當下目標身上有沒有新印記」分辨刷新／被切掉／過期，那依賴「引擎先加新效果、再送舊效果的 finish」這個未驗證順序（第 11 節第 7 題）。改成不依賴順序的做法：

- 任何 `ESSBMark` 實體結束時（不管原因），只做一件事：`Ctl.LeaveEmber(target, X)` → 對目標套 `ESSB_Ember_X`（1 秒、單階標記、KWDA `[ESSB_Ember_X, ESSB_EmberAny]`、原型 0、帶小腳本 `ESSBEmber`）。
- **開印版**新印記 `OnEffectStart`（不管哪個元素 Y）：`HasMagicEffectWithKeyword(ESSB_EmberAny)` 為真 → 找出是哪個 X（最多 11 次 `HasMagicEffect`）：X ≠ Y → 這是**被切掉**，跑 X 的終焉（接管元素 = Y），再跑 Y 的開印；X == Y 不可能（同元素走刷新版）。然後 `DispelSpell(Ember_X)`。沒有餘燼 → 純開印。
- **刷新版**新印記 `OnEffectStart`：有 `Ember_Y`（同元素）→ 這是刷新，只 `DispelSpell(Ember_Y)`，不反應。
- `ESSBEmber.OnEffectFinish`（1 秒自然到期，沒有任何新印記來接）：目標活著且沒有 `ESSB_BurstDone` → **過期終焉**；有 `ESSB_BurstDone` → 融斷已由控制器結算，什麼都不做。
- 融斷：控制器對每個目標先套 `ESSB_BurstDone`（2 秒單階標記），跑終焉，再 `DispelSpell(印記)`；印記 finish 留下的餘燼到期時看到 `BurstDone` 就閉嘴。
- 全部是目標自己身上的效果與存在測試（I1～I6 不變）；餘燼 1 秒遠長於兩個 Papyrus 事件的間隔，順序無所謂。代價：每次印記結束多一次 `DoCombatSpellApply`（餘燼）。第 11 節第 7 題因此從「假設」變成「不需要」。

### 4.8 水的長流回魔（使用者追加，已定）

- 規則：水形態下每秒回復「水形態魔力維持費的 80%」；不吃熟練／大師／長河的成長，不給同伴（alter 5.11 與總表第 23 條）。
- 實作：不新增 tick、不新增持續型法術。`ESSBElem3.WaterFormTick`（`ESSBElem3.psc:1106-1130`，已是控制器每秒 tick 的一部分，決定 32）在 `ApplyUtil(4, health)`／`ApplyUtil(6, stamina)` 之後多一行 `akCtl.ApplyUtil(5, magicka, 0, player)`；`magicka = 水形態的維持費 × 0.8`，維持費公式沿用 `ESSBFormRules.MagickaUpkeep`（`ESSBFormRules.psc:59-75`：`GetActorValueMax("Magicka") × 基礎% × (1 − 0.7 × 樹等級／100) × ESSB_MultUpkeep`）——把它搬成 `ESSBController.UpkeepFor(element)` 讓 FormRules 與 WaterFormTick 共用同一個函式，兩邊永遠算同一個數。
- 倍率：這一份**不乘** `ESSB_MultRecovery`（回復滑桿），只跟著 `ESSB_MultUpkeep`——否則回復滑桿 >1.25 就會把「差一點」變成淨賺；`ApplyUtil` 已有繞過回復倍率的參數（神佑 1 HP 走的那條，fix round 7 的表），照用。
- 長河（同調三段給同伴）：同伴迴圈只回血回耐，不加魔力。
- 改名：水樹開啟熟練分支「回流」→「湧泉」；只改 PERK 的 FULL／DESC 與 CSF 文字，EDID `ESSB_P_water_1_1_B1` 不變（EDID 是對外契約）。無元素樹的「回流」不動。
- 排程：第 2 期（能力層），round 18 不碰。

### 4.5 〔作廢，N2 起〕雷的 best-of-N 近似：DLL 在命中時精確擲「1～25、N 次取最大」並以 magnitude 覆寫套用；本節只留作 N1 期間的紀錄

目標分布：擲 N 次 U{1..25} 取最大，N = 1 + 電荷階（0..3）。引擎法術強度固定，所以量化成五檔 R1..R5 = 3／8／13／18／23（各代表 1–5、6–10、11–15、16–20、21–25 的中點）。第 j 檔的目標機率 P_j(N) = (j/5)^N − ((j−1)/5)^N：

| N | R1 | R2 | R3 | R4 | R5 | 期望（真值） |
|---|---|---|---|---|---|---|
| 1 | .200 | .200 | .200 | .200 | .200 | 13.0（13.0） |
| 2 | .040 | .120 | .200 | .280 | .360 | 17.0（17.3） |
| 3 | .008 | .056 | .152 | .296 | .488 | 19.0（19.5） |
| 4 | .0016 | .0240 | .1040 | .2704 | .5904 | 20.0（20.8） |

誤差 ≤ 0.8（量化損失，永遠偏低），分布形狀正確（高電荷時低值變稀有）。

進入點寫法取決於第 11 節第 1 題（同一進入點多段同時成立時引擎的行為）；生成器同時支援兩種，`settings.json` 的 `lightning_roll_mode` 預設 `chain`，探針證明是「全部套用」時改 `additive`——這是實作開關，不是設計待定：
- **首段成立即停（chain）**：五段依 R5→R1 排，條件 `GetRandomPercent(77) < p_j`，p_5 = P_5，p_4 = P_4/(1−P_5)，p_3 = P_3/(1−P_5−P_4)，…，R1 段無機率條件。每段獨立擲骰，鏈式機率正好還原 P_j。
- **全部成立都套（additive）**：R1 段無條件（強度 3），另四段各套「+5」的增量法術 `ESSB_Hit_Lightning_Inc`，條件 `GetRandomPercent < q(N)`，q = 0.5／0.68／0.77／0.825（讓期望 = 3 + 20q 對上 13／16.6／18.4／19.5）；形狀是二項分布，比 best-of-N 更集中（N=1 時變異數 25 對 52），期望誤差 ≤ 1.3。這是退路，不是首選。
- 段數：4 攻擊變體 × 4 電荷階 × 5 檔 = 80（chain）或 4 × 4 × 5 = 80（additive）；`GetRandomPercent` 是 0–99 整數，機率解析度 1%。電荷階條件 `HasMagicEffect(電荷 T{k})` 在分頁 0；電荷階梯在第 3 期才上線，第 1 期先以 N=1 的五段落地（20 段）。
- 其他元素：區間都是 ±1，不做隨機（指揮官定案）。

### 4.4 切換的生效時機：下一刀就是新元素，沒有腳本來回

使用者問的「切換多快生效」，在引擎驅動的附傷路徑下答案是：**按下切換到下一次命中之間不需要任何腳本來回**。機制：`ESSB_P_HitProc` 每一段附傷、印記、升階的條件都讀 `GetGlobalValue(ESSB_CurrentElement)`（0x000812）與 `GetGlobalValue(ESSB_FormActive)`（0x000813），引擎在命中那一幀評估；這兩個 GLOB 由切換函式用原生 `GlobalVariable.SetValueInt` 寫入（今天在 `ESSBController.SwitchForm`，`ESSBController.psc:1335-1336`）。寫入是原生呼叫，不經任何其他腳本實體的鎖。

可能殘留一刀的舊值只有三種，都有對策：
1. **切換函式本身排在忙碌的控制器後面。** 今天 `SwitchForm` 在 Controller 實體上，控制器在跑 Tick 時，力量的 `OnEffectStart` → `ToggleForm` 要等鎖（log 裡 `ESSBFormPowerEffect.OnEffectStart` 也在排隊：Frequency 9／3）。對策：熱鍵與力量都先經過一支**輕量、平時閒置**的別名腳本 `ESSBInput`（新檔，只有 `OnKeyDown`／被力量呼叫的 `RequestSwitch(element)`）：它先用原生呼叫寫 `ESSB_CurrentElement`／`ESSB_FormActive`（並依 alter 1.1 的開形態魔力門檻先判一次），**然後才**呼叫 `Controller.SwitchForm` 做其餘的事（換能力、重寫法術強度、同調、音效、印記切換）。即使控制器忙，引擎已經看到新元素。控制器隨後執行時以 GLOB 為準，不再自己判斷「要切到誰」。
2. **新元素的法術強度尚未寫入。** 每個元素有自己的 `ESSB_Hit_*`，若本次遊戲還沒為該元素寫過 magnitude，引擎用 ESP 預設值（平均值 ×1.0，沒有 G(L)）。對策：`RefreshProcMagnitudes` 在 `Setup`、樹升級、投點、MCM 改倍率時對**全部 11 個元素**重寫（約 60 次 `SetNthEffectMagnitude`，都是低頻事件），切換時只需重寫「隨形態改變的項」（開印加成、嗜血、熔身這類窗口本來就只影響當前元素）。這樣切換後的第一刀就是正確的基礎值；最多只有「切換後 5 秒開印加成」這種窗口晚一點生效。
3. **形態能力（維持費、Ordinator 學派條件用的 keyword）** 仍由控制器 `AddSpell/RemoveSpell`，會晚到；它們不影響附傷段的條件，只影響維持費起算與武器光——武器光晚 0～數秒亮起是可見的，若不能接受，武器光也可改成「條件式常駐能力讀 GLOB」（引擎每秒重算，晚最多 1 秒，但不依賴控制器）。

`IsPowerAttacking`／`IsSneaking`／目標階的條件都是引擎當下的值，沒有殘留問題。結論寫進 alter 1.1.1。

---

## 5. 生成器要吐出的記錄（`build_v03.py`）

以下是類別與數量級，實作者以一張表驅動生成，不要手寫 300 段。所有數值來源仍是 `settings.json`（新增 `ladders` 區：每階秒數、成熟秒數、等價層數、倍率），與 alter 2.3 的表一一對應。

| 類別 | EDID 樣式 | 數量（估） | 備註 |
|---|---|---|---|
| KYWD | `ESSB_MarkAny`、`ESSB_Ladder_<L>` ×17、`ESSB_Cool_<L>` ×13、`ESSB_Tier_<L>_<k>` ×~55 | ~90 | 階關鍵字讓 699 能一次讀「任一階」 |
| MGEF 印記 | `ESSB_MarkOpen_<X>`、`ESSB_MarkRefresh_<X>` | 22 | 兩者 KWDA 同（`ESSB_Mark_X, ESSB_MarkAny, ESSB_Element_X`），驅散 `ESSB_MarkAny`；開印版帶 `ESSBMark`（`IsOpen=True`）與 `ZZArt_X` 閃現，刷新版帶 `ESSBMark`（`IsOpen=False`）不播特效；沿用 `MGEF_MARK_FLAGS | 0x1000 | 0x10000000`（No Death Dispel，round 15 已加） |
| SPEL 印記 | `ESSB_MarkOpenSpell_<X>` = `[MarkOpen_X, 該元素第一階 T1, Cool1]`；`ESSB_MarkRefreshSpell_<X>` = `[MarkRefresh_X]` | 22 | 水 10 秒；duration 由生成器寫 |
| MGEF 目標階 | `ESSB_<L>_T<k>`、`ESSB_<L>_Cool<k>` | 17 + 11 | 凍結 3、血痕 4（DoT）、水壓 3、詛咒 4、星痕 3（引信）；灼熱與聖印目標階撤銷（火熱度改自身、聖印改單一印記）；中毒改單一效果 |
| SPEL 目標階 | `ESSB_<L>_Promote<k>`、`ESSB_<L>_Refresh<k>`、頂階 `ESSB_<L>_Top` | ~55 | |
| MGEF/SPEL 自身階 | 電荷 4、岩甲 4、起風 1、熱度 4（含熔爐；白熱／熔燒另各一顆披風 MGEF + 關聯傷害 SPEL + 披風火印記 MGEF）、戰意 3、冰盾 3、水鏡 3、聖佑 3、同調 3 + 對應 Cool | ~45 + ~42 | 岩甲每階是原版石膚型護甲增益（`FID_KW_ARMOR_SPELL` 驅散互斥不用，改用 `ESSB_Ladder_Rock`） |
| MGEF 已交戰 | `ESSB_EngagedEffect` | 0 新增 | 嵌進每個 `ESSB_Hit_*` 為額外 EFID（30 秒）；先前提議的 `ESSB_LastHitEffect_*` 撤銷（決定 4） |
| 中毒〔決定 1〕 | `ESSB_PoisonEffect`（值修正 AV 24、Detrimental、Hostile，帶 `ESSBPoison` 腳本）+ `ESSB_PoisonSpell`；催毒 `ESSB_VenomEffect/Spell`（同形，8 秒） | 4 | 中毒階梯與擴散 AME 撤銷 |
| 雷五檔〔決定 7〕 | `ESSB_Hit_Lightning_<Normal|Power>_R1..R5`（強度 3／8／13／18／23，重擊 ×1.5） | 10（取代原 2） | 進入點：4 攻擊變體 × 4 電荷階 × 5 檔 = 80 段，條件加 `HasMagicEffect(電荷 T{k})`（分頁 0）與 `GetRandomPercent`（77）；順序與機率見第 4.5 節 |
| 聖佑〔決定 8〕 | `ESSB_Divine_T1..T3` + Cool ×3 + 頂階聖光爆 `ESSB_DivineBurst`；目標側聖印階梯撤銷 | +7 MGEF | 0x23 段 ×3（武器傷害 +10／20／30%）、0x1D 段 ×3（聖傷 +10／20／35%）條件分頁 0 讀自身效果 |
| SPEL 附傷 | 既有 22 + `ESSB_Hit_Wind_SneakNormal/SneakPower` + `ESSB_Hit_Blood_<N/P>_B1..B3` | 30 | 魔法值預設寫平均值；`SPIT` 不變 |
| PERK | `ESSB_P_HitProc`（隱藏、不可玩，`Setup` 加一次） | 1 | 段落：附傷 58（分頁 0：`GetGlobalValue` 74 ×3、`IsPowerAttacking` 673、`IsSneaking` 286、`GetEquippedItemType` 597 param 1 ≠7/≠12 或 =7 OR =12、`GetActorValuePercent` 640 AV 24 四區間；分頁 2：`GetPlayerTeammate` 453 == 0、`IsCommandedActor` 700 == 0、`GetDead` 46 == 0、`IsBlocking` 569 == 0）；印記 22；階梯升階／刷新／重擊免等待 ~50；自燃 1、風刃由腳本 |
| 既有 PERK 追加 | 0x1D「Mod Spell Magnitude」~22 段、0x23「Mod Attack Damage」~5 段 | 27 | 放在 `ESSB_P_HitProc` 或對應節點 PERK 上（節點類放節點，基礎類放 HitProc） |
| GLOB | `ESSB_DivineArmed` | 1 | Guard 早退用 |
| 特效〔alter 2.11／2.12〕 | `ESSB_FormAbilityEffect_<X>`（`build_v03.py:1409-1413`）的 `hit_shader`／`enchant_shader` 清為 0（拿掉全身光環）；`ESSB_SyncGlowEffect_1..3`（1384-1390）不再掛進形態能力；`ESSB_SyncWeaponEffect_<X>`（1393-1398）改為三顆亮度版本 `_Dim/_Mid/_Bright`（各自一筆 EFSH，由 `fx_extract` 調 `EFSH_FLOATS` 的透明度），形態能力的效果層改為 `[武器光 Dim（無條件）, Mid（SyncStage>=2）, Bright（SyncStage>=3）]` 互斥條件；切換音效只保留 `FormActivate_新`；自身資源階 MGEF 不掛著色器，頂階 SPEL 附一個 SNDD | −11 綁定、+22 MGEF、+22 EFSH | 現行 `ESSB_SyncWeaponEffect` 是否真的只在武器上顯示（AbOnFire 手法：常駐能力的 enchant shader）尚未實機證實（medium）；若顯示在身體上，退路是壓低 EFSH 透明度到只有手部可辨（alter 2.11 的 (c)） |
| 熱鍵 | 新腳本 `ESSBInput.psc`（`ReferenceAlias`，alias 0 第四支）：`OnPlayerLoadGame/OnInit` → `RegisterForKey` ×11（鍵碼由 MCM GLOB `ESSB_Hotkey_<X>` ×11 提供，預設 Numpad）；`OnKeyDown` → 若 `Utility.IsInMenuMode()` 或文字輸入中則忽略 → 寫兩個 GLOB → `Controller.SwitchForm`；11 個形態力量的 `ESSBFormPowerEffect` 也改呼叫 `ESSBInput.RequestSwitch` | +11 GLOB、+1 腳本、schema 升版 | `Form.RegisterForKey(int keyCode)`／`OnKeyDown`（`vendor/imports/Form.psc:163,167`，SKSE 提供） |

進入點總數約 167 → 320。FormID：第 2 期起由生成器按家族分段連續配號並在建置輸出印出每段範圍（存檔相容性已解除，見第 6 節「限制解除」）；第 1 期仍在既有空段配號（`0x005170–0x005181` 已被 round 16 的防護視窗占走，`0x006000+` 是任務段）。`entry()`（`build_v03.py:807-818`）加 `epft`／`function` 參數；`ctda()`（`738-740`）加 NotEqual（`0x20`）與 OR（`0x01`）。`validate_delivery`（`3391-3423`）的 contact 名單改為前綴驅動（`ESSB_Hit_`、`ESSB_Mark`、`ESSB_<L>_`、`ESSB_React_`）。

**刪除的記錄**：`ESSB_StatusHostEffect/Spell`（`1560-1571`）、`ESSB_EngagedEffect/Spell` 獨立記錄（`1573-1584`，改嵌）、`ESSB_MarkEffect_<X>`／`ESSB_MarkSpell_<X>`（改成 Open/Refresh 兩套）。FormID 身分規則：新 EDID 用新 ID；被刪的 EDID 留 inert stub（同 round 9 的 stub 做法）以免舊存檔的效果引用懸空。

---

## 6. 逐檔變更與分期（每一期都可獨立部署、可玩）

### 第 1 期（round 18）：附傷走引擎 + 便宜修法（不動狀態層）
1. `build_v03.py`：`ESSB_P_HitProc` 的附傷段（58 段，雷改為五檔 ×4 變體 = 20 段，合計 74）、已交戰嵌入附傷法術、風潛行／血區間法術、`ESSB_DivineArmed`；修 693→699（浴火、水膜、影甲）；`HITPROC ok` 驗證（真值表：`FormActive∈{0,1} × Element 0..11 × IsPowerAttacking × IsSneaking × 右手型別{0,1,7,12} × HP% 四區`，形態開啟且元素 ≥1 時恰好一段成立、否則零段；標記旗標；delivery）。
2. `ESSBController.psc`：`RefreshProcMagnitudes()` 與觸發點（`Setup` 1190、`SwitchForm` 1335-1337 之後、`OnSyncStage` 3380、`RefreshTrees` 3003、`RefreshAbilities` 3046、`RefreshRuntimeValues` 6921、`SetOpenBoost` 4311／`SetEndBoost` 4328／`SetBloodthirst` 4989／`SetMolten` 4213 及其到期、`AddSelf`／`ClearSelfAll` kind 4、`EnvCheck` 4094 的 `EnvNight` 變化、`OnFormSwitched` 1430）；`SyncStage()`（3315）快取；`ESSBNodes.Rank/Br` 改讀 Controller 鏡射陣列（`Trees.RefreshTree` 547／`RefreshActive` 618 尾端匯出）；**`ApplyProc`（1781）改為「差額補丁」，不是縮成補刀**（裁定見本期末尾的「分期裁定」）：引擎用 `ESSB_P_HitProc` 套基礎附傷 `base = B × R × BaseDamageMult × G(L) × M_player`；腳本在同一次 `OnWeaponHit` 裡照舊算 `full = base × M_target`（`M_target` = 今天 `GetHitMult`（2971）裡**讀目標或一次性旗標**的每一項：`ESSBElem.HitMult` 的熱度層、冰封 +2%／點、電蝕、聖印／聖痕／驅魔、水壓、虛空、星痕弱點、火域；`ESSBElem2.TargetDamageMult` 的御風失衡、空中追擊浮空；`ESSBElem3.TargetDamageMult` 的詛咒滿層、星鎖、星域；`OpenStrikeMult`（開印那一擊 ×1.5）；`KillStreakMult`），只在 `full − base > 0` 時以 `ESSB_Hit_<X>_Bonus`（無特效副本法術，第 5 節）`DoCombatSpellApply` 一次差額；差額 ≤ 0 完全不跑（也不呼叫任何 `GetStack`——先用 `Rank/Br` 判「有沒有任何目標側節點或狀態可能成立」再讀目標）。`RollBase` 不再用：非雷元素以平均值為 `B`，雷以 13（N=1 的期望）為差額基準（引擎那一份是五檔，差額用期望值，誤差 ≤ 0.8×M_target−1，可接受）。極致、雙生、餘響、順勢照舊呼叫（極致與雙生改用烤好的主法術 `DoCombatSpellApply`，不含差額）。`OnWeaponHit` 另**無條件** `NoteDamageElement(target, element)` 一次（今天由 `ApplyTrackedDamage` 做，附傷走引擎後腳本看不到那一擊；round 14 的擊殺歸屬要撐到第 2 期才刪）。雷的五檔法術與 N=1 的 20 段（4.5）；`AddSync`（3310-3312）刪每擊 `RefreshDivineProtection`；`RefreshDivineProtection`（7348）寫 `GDivineArmed`，新增 `OnLethalHitWhileArmed()`。
3. `ESSBGuard.psc`：本地 GLOB 屬性 + `NodeBits`；`OnHitEx`（68-173）改為「無事可做零跨實體」；刪 89 行。
4. `ESSBInput.psc` 與 11 個熱鍵 GLOB、MCM 熱鍵頁（預設開啟）；`ESSBFormPowerEffect` 改呼叫 `ESSBInput.RequestSwitch`；`SwitchForm` 改為以 GLOB 為輸入（4.4）。
5. 特效：形態能力去掉全身光環、武器光三檔常駐、切換零轉場、切換提示（Notification，MCM 可關）（alter 2.11／2.12、本檔第 5 節特效列）。
6. `settings.json` `state_schema_version` 6→7（新成員），lock 隨建置生成。
- 可玩性：完整；狀態層照舊（含它的 bug）；**數字與今天完全相同**（基礎 + 差額 = 舊 `ApplyProc` 的乘積；Astra 的 harness 例：熱度 4 仍是 15.246，只是 11.55 由引擎先落、3.696 由腳本補）。
- **手感（不粉飾）**：這一期玩家拿到的是「刀一砍到，基礎附傷的數字、衝擊特效、音效、雷的削魔同幀出現」；差額、印記、反應、狀態層數仍走 Papyrus，仍會晚 0～數秒。差額在沒有目標側狀態時（第一刀、非火形態、目標沒層數）是零成本；有狀態時每擊仍有一次腳本側讀目標（`GetStack` 會跨到宿主 AME，最壞連帶宿主 tick）——所以火形態連砍時的「越打越燙」那一份仍會晚到，只有基礎那一刀變快。Guard 早退、`SyncStage` 快取、Trees 鏡射把我們自己塞進佇列的 stack 砍掉大半（dump 裡 262+241+251+158），這是延遲改善的主要來源；差額補丁不抵銷它，但也沒有讓命中路徑歸零。
- 風險：magnitude 觸發點漏掉（附一張「變數 → 寫入點 → 已呼叫」對照表進實作紀錄）；讀檔後 2 秒內用 ESP 預設值（可接受）；差額與基礎分兩次落地，擊殺結算可能落在差額那一次（`NoteDamageElement` 無條件記錄補上）。

**分期裁定（Astra 於第 1 期提出的矛盾）**：採**差額補丁**。理由：(1) 今天的乘積是 `base × M_target`，目標側的每一項在第 1 期都沒有引擎表示，硬砍會讓玩家先掉一段傷害（實測 11.55 對 15.246）；(2) 把整個 `ApplyProc` 留到第 2 期再換等於第 1 期沒有原生附傷，延遲改善只剩便宜修法；(3) 差額補丁隨第 2、3 期把每一項搬進 0x1D／0x23 條件而**自然歸零**，最後只剩連殺 ×2 這個一次性旗標（永遠是腳本），整段可以縮成一行。代價：第 1 期每擊仍可能有一次腳本讀目標，見上。**第 1 期仍由腳本負責、以及各自在哪一期消失**：熱度層（→第 2 期，火的熱度改為你身上的階梯，0x1D 讀分頁 0）、冰封 +2%／點、水壓、詛咒滿層、星痕弱點、星鎖、星域、聖印／聖痕（→第 2 期，目標階梯與印記，0x1D 讀分頁 2）、電蝕（→第 2 期，0x1D 分頁 2 `GetActorValuePercent(Magicka) == 0`）、御風失衡、空中追擊浮空（→第 2 期，0x1D／0x23 分頁 2 讀既有單階標記）、火域（→第 2 期，0x1D 讀 `ESSB_DomainFire` GLOB）、開印 ×1.5（→第 2 期，印記走引擎後以「目標沒有本元素印記」條件表達）、驅魔對死靈施法者（→第 2 期，分頁 2 `GetInFaction`／`GetIsClass`，決定 67 的三個判定合併）、連殺 ×2（永遠腳本）。

### 第 2N 期（round 19，使用者裁決「單純走丙、給網路」）：SKSE 原生命中插件取代 entry 51 附傷段
**切片 1（現在派 Astra）**：
1. 查證：把 4.11 待查證表逐項換成實際 API 名稱、簽名、CMake 相依與 SKSE 1.5.97 匯出方式，寫進 `build/native-verification.md`（之後併回 4.11）。
2. 新專案 `native/`（CMake、CommonLibSSE(-NG)）：`TESHitEvent` sink、manifest 載入、與 round 18 `HITPROC` 真值表**逐格相同**的選法術表（形態／元素／重擊／潛行／弓弩／血位區間／雷五檔）、`ESSB_NativeHit` GLOB、`ESSBNative` 原生函式、版本檢查與自我停用、log（4.11 溝通段的定案位置與格式）。
3. `build_v03.py`：產生 `SKSE/Plugins/ElementsSpellblade/manifest.json`；新 GLOB `ESSB_NativeHit`；**移除 `ESSB_P_HitProc` 的 entry 51 附傷段**（0x1D／0x23 段與其他進入點不動）；MCM 一般頁加「原生命中（DLL）」開關與版本字串；`HITPROC ok` 改為比對「DLL 的選擇表」與同一張真值表。
4. 狀態層、腳本差額補丁（第 1 期的 `ApplyProcBonus`）、印記、反應**照舊不動**。
5. 探針卡 2N（10.2）。
**切片 2（之後）**：印記開印／刷新、目標階梯升階／刷新、開印 ×1.5 改由 DLL 選法術（第 2 期的內容），效果層條件降為雙重保險。
- 可玩性：完整；DLL 缺席、版本不符或 MCM 關閉時**沒有元素附傷**（使用者已接受），回退＝還原 round 18 套件。
- 風險：建置鏈；崩潰（4.11 的保險）；`CastSpellImmediate` 是否發 `OnSpellCast`（探針 N-5，沒有退路，失敗即回報）。

### 分工原則（使用者核准 2026-09-22）：狀態放在引擎、判斷放在 DLL、介面留給 Papyrus

- **引擎持有一切需要存活過存檔的狀態**：印記、目標階梯、自身階梯、成熟計時、引信、DoT、防護視窗、火源披風——全是目標或玩家身上的魔法效果，時間就是效果的 duration；GLOB 存開關與鏡射；perk 存投點。DLL **不序列化任何東西**：它唯一的「記憶」是啟動時載入的不可變 manifest，和單次事件處理內的區域變數（例如「這次驅散是我自己做的」的重入旗標，事件結束即消失）。
- **DLL 做每一個「命中那一幀要決定的事」**：讀目標與玩家身上有什麼、算數字、套哪幾顆法術、套幾次。
- **Papyrus 留介面與低頻**：MCM、CSF 技能樹、洗點、形態提示、記錄定義、每秒維持費類、需要 Papyrus 專用 API 的（神佑延遲死亡、CSF 加經驗、復生的 AI 與召喚上限）。
- **使用者永遠停在 1.5.97**：DLL 只支援 SE 1.5.97 單一執行期（SKSE 2.0.20、Address Library `version-1-5-97-0.bin`），用 CommonLibSSE 單執行期即可；「升級要重建」不再是代價，本檔其他地方的相關敘述一併作廢。

**對草案的審查（放錯邊／漏掉的）**
1. 「DLL 不存狀態」在每個機制上都站得住，條件是**所有時間都是效果的 duration、所有計數都是效果的 magnitude**：同調計數＝效果的 magnitude（2026-09-22 還原 v0.3）、白熱引信＝T3 的 duration、退階＝到期時套低一階、毒的時長＝DoT duration、防護視窗＝round 16 的原生 MGEF。唯一需要「時序回呼」的是**到期事件**（過熱、星痕引爆、死咒、浮空落地、印記過期、退階）：DLL 若能接引擎的效果移除事件（`TESActiveEffectApplyRemoveEvent`，待查證），這些回呼全部進 DLL，`ESSBFuse`／`ESSBEmber`／`ESSBTierDecay` 與 4.9 的餘燼標記整個不需要——因為「被切掉」由 DLL 在命中內自己做（先跑舊印記終焉再套新印記，不靠事件順序），「過期／死亡」由移除事件告知。若該事件不可用或不同步，這幾支小 Papyrus 腳本保留（它們是實作選項，不是退路）。
2. 漏掉的：**經驗**（`CustomSkills.AdvanceSkill` 是 Papyrus API）→ DLL 每擊送 ModEvent `ESSB_XP(element)`，Papyrus 晚一點加無妨；**連殺的潛行事實**→ DLL 在潛行命中時給目標掛 1 秒 `ESSB_LastHitSneak` 標記，死亡時讀它（不存變數）；**反應本體**（開印／終焉的推力、恐懼、復生、範圍掃描）→ 第二優先切片才搬，之前由 DLL 送 ModEvent 觸發現有 `ESSBReactions`（晚到與今天相同）；**毒的擴散計時**→ 不用 DLL 計時也不用 Papyrus `OnUpdate`：中毒 ≥5 劑時 DLL 另掛一顆「瘴氣披風」（原型 35，半徑 3 公尺，關聯法術＝對鄰居套 0.5 劑），引擎每秒自己傳（設計數字從「每 2 秒 1 劑」改「每秒 0.5 劑」，寫進 alter 5.10）；**熱鍵**→ 可留 `ESSBInput`（輕量實體），DLL 版輸入 sink 列為選配。
3. 放錯邊的：草案把「附傷強度改由 DLL 命中時計算」放第二優先——它應該在第一優先的第一片之後立刻做，因為它刪掉的是第 1 期最大的風險（`RefreshProcMagnitudes` 的十幾個觸發點對照表）與 4.5 的雷五檔；用即時施放的 magnitude 覆寫參數（待查證）就不必再改共用法術的 magnitude，I7「共用法術只有一個寫入者」也自然成立。連帶**恢復兩個 v0.3 原設計**：每擊隨機 B（所有元素在區間內擲骰，不再固定平均值）與血位**線性**曲線（不再四段階梯）——alter 第 5、15 條改回。
4. 每秒計時（維持費、火源代價、水回魔、環境）：同意最低優先且**留在 Papyrus**；沒有 hook 就沒有乾淨的 C++ 每秒點，`ESSBFormRules.OnUpdate` 每秒一次很便宜。
5. 神佑延遲死亡：留 Papyrus（`StartDeferredKill` 的 C++ 對等未查證）。

### DLL 切片（第 2N 期起，每片獨立驗證、有探針卡、可整包回退）

| 片 | 內容（DLL） | 原計畫照做 | 改由 DLL 做 | 直接刪掉 | 崩潰面 | 回退 |
|---|---|---|---|---|---|---|
| **N1**（round 19，進行中） | 命中附傷：`TESHitEvent` sink、manifest、與 round 18 真值表逐格相同的選法術表、`ESSB_NativeHit`、log | 第 1 期一切 | entry 51 附傷段 | `ESSB_P_HitProc` 的 entry 51 段 | 一個事件 sink，處理玩家的武器命中 | 還原 round 18 套件 |
| **N2** | 命中時算強度：DLL 讀 GLOB（`ESSB_Lvl_*`、`ESSB_BaseDamageMult`、MCM 倍率、`ESSB_SyncStage`）、玩家 perk（節點）、玩家血量%，算 `B（區間擲骰）× R × G × M_player`，用 magnitude 覆寫參數即時施放；雷在 C++ 擲「1～25、N 次取最大」（N＝電荷階，N4 前固定 1）；血位線性內插；**雷暴擊判定〔已定 2026-09-23〕**：雷是全模組唯一會暴擊的元素，暴擊率 = 基礎 5% + 每格電荷 +2%，套在附傷與放電上，一般暴擊 ×1.5、電荷滿格時的重擊放電必定暴擊 ×2.5；**命中吸血〔已定 2026-09-23〕**：基礎吸血（依血位占附傷比例）與附傷同一刀由 DLL 算出並回血 | 狀態層、差額補丁（目標側倍率暫留 Papyrus） | `RefreshProcMagnitudes` 的全部觸發點；雷五檔；血四區間法術 | 4.5 整節、雷五檔 SPEL 與 20 段、血 B1～B3 法術、風潛行變體法術（改倍率）、第 1 期「變數→寫入點」對照表 | 純算術與 perk 讀取，仍只在命中 sink 內 | 還原 N1 套件 |
| **N3** | 目標狀態層→引擎效果，由 DLL 掛：開印版／刷新版印記（切掉在命中內處理）、階梯升階／刷新／頂階（含冰封、碎冰真傷）、中毒讀取—疊加—重套（magnitude 覆寫，不改共用法術）、瘴氣披風、火熱度與聖佑自身階梯（因為它們取代目標狀態）、目標側倍率（讀目標效果，差額補丁廢除）、開印 ×1.5；過期／死亡回呼走效果移除事件（待查證，否則保留 `ESSBMark`＋餘燼、`ESSBFuse`、`ESSBTierDecay`）；反應本體暫以 ModEvent 觸發 `ESSBReactions`；**浸濕滿層觸發沖刷〔已定 2026-09-23〕**：命中疊浸濕、發現滿層（且是重新疊滿，不是掉層前的殘留）時，清除目標身上「施法得來、有持續時間、屬增益」的效果，排除種族能力／任務腳本效果／天賦／疾病／本模組自己的印記與階梯，待查證：可清除效果的精確判定條件、效果套用事件 | 反應本體（Papyrus）、餘燼（視查證）、擊殺看印記的 Papyrus 判定 | `ESSBStatus`、登記表、pending、swap、差額補丁、擊殺歸屬、4.10 的效果層條件 | `ESSBStatus.psc`、`ESSBPoison.psc`、`ESSBSpread.psc`、4.10 的表、`ApplyProcBonus`、0x1D 段裡讀目標階的段（DLL 直接乘） | 命中 sink 內多套幾顆法術；效果移除事件 sink（新）；讀目標效果列表 | 還原 N2 套件 |
| **N4** | 玩家受擊與自身資源：同一個 sink 處理目標＝玩家的命中：岩甲／冰盾／水鏡降階、反震、灼身、寒反、靜電、毒皮、殘影／影身、反擊／反噬／破護；電荷、岩甲、起風、戰意、同調、冰盾、水鏡階梯的升階；雷的 N＝電荷階；風的多段觸發 N 次迴圈；連殺的 `ESSB_LastHitSneak`；**聖佑減傷〔已定 2026-09-23〕**：依聖佑階套用受到物理傷害 -5／-10／-15% 與魔抗 +10／20／35%（引擎原生魔抗，受 85% 上限）；**雷滿格法術麻痺〔已定 2026-09-23〕**：電荷滿格時命中正在詠唱的敵人，30% 機率中斷其施法；**反咒、斷咒改走 DLL〔已定 2026-09-23〕**：反咒改讀 DLL 的施法事件（施法者帶破魔印時觸發，讀該次施法消耗魔力算真傷）；斷咒改為 DLL 命中時讀目標施法狀態並中斷（同雷滿格法術麻痺的技術）；以上待查證：施法事件（spell-cast event）、命中時讀取目標施法狀態、中斷施法 | `ESSBGuard.OnActorKilled`（暫留） | `ESSBGuard.OnHitEx` 整段、`SelfCharge` 等計數、`AddSync/SyncStage`、`WindEcho` | `ESSBGuard.psc` 的受擊路徑、自身計數與其鏡射的寫入、`ESSBInput` 以外的每擊 Papyrus | 受擊時的推力若用原生 API（待查證）是新的崩潰面；先用 ModEvent 交 Papyrus 推 | 還原 N3 套件 |
| **N5** | 融斷範圍掃描與結算、死亡處理（`TESDeathEvent` 待查證：看印記化灰／亡者歸來的**判定**、毒的死亡擴散、連殺）、反應本體中「套法術」的部分改表驅動；推力、恐懼、復生、召喚上限仍 ModEvent 交 Papyrus | 神佑、復生 AI、恐懼、推力（Papyrus） | `OnFormClosed` 的掃描、`OnKillEvent` 的判定、`ESSBReactions` 的傷害與狀態部分 | `ESSBGuard.psc` 全檔、`ESSBReactions` 裡純套法術的分支 | 範圍掃描（走引擎的 process lists）是最大的面；死亡事件 sink | 還原 N4 套件 |
| **N6**（最低） | 每秒計時（維持費、火源代價、水回魔、環境）、熱鍵輸入 sink | 全部（Papyrus 每秒一次已夠便宜） | 只有在 N1～N5 後仍量到 Papyrus 每秒工作造成延遲時才做 | — | 若做：一個每幀或計時 hook，是全案最大的崩潰面，所以最後且可不做 | — |

**妥協盤點與還原項**：alter 相對 v0.3 的每一項改動、哪些是被 Papyrus／entry 51 逼出來的、DLL 能不能還原，逐項在 `design-compromises-2026-09-22.md`（附勾選總表）。使用者勾選後，各還原項落在：N1／N2（A9 隨機 B 與血位線性已還原、A10 命中旗標）、N3（A1a 血痕層數、A2 凍結量表、A3 詛咒 13 階、A4 水壓與星痕階數、A8 開印／上限／萬象節點、A12 雙印、A13 去餘燼）、N4（A6 自身資源計數、A7 同調計數、A8 極致／追擊／疾攻／節奏）、N5（A1b 放血依當下生命——需每秒點、A15 火葬／亡魂事後判定）、N6（領域 Hazard，選配）。「層數放效果強度、階數＝上限」是還原的兩個技術，DLL 仍不存任何狀態；唯一需要每秒執行點的是放血。

每片交付：`native/` 版本號 +1、`build/native-verification.md` 對應章節、探針卡（10.2）、`HITPROC ok` 擴充為該片的離線斷言（DLL 選擇表對真值表；N2 起加「同一輸入 1000 次擲骰的分布」）。每片的回退都是「還原上一片的完整套件」，沒有開關式退路。

**分期斷裂總檢（DLL 版）**：任何效果的 Papyrus 路徑只能在它的 DLL／引擎表示上線的同一片被刪。N2 刪強度重寫時目標側倍率仍由差額補丁提供（到 N3）；N3 刪狀態容器時自身計數不動（到 N4）；N3 的印記反應以 ModEvent 觸發現有 Papyrus（到 N5）；N4 刪 `OnHitEx` 時 `OnActorKilled` 留到 N5；雷的 N 在 N4 前固定 1。

### 第 4 期：實機調參（alter 8 的清單，預設值已定）。

### 限制解除：存檔相容性整套不做（使用者 2026-09-20 晚：「等模組完善才開新檔，不留舊檔」）

從第 2 期起適用（第 1 期的 6→7 由 Astra 照做，成本低、不打斷）。拿掉的：
1. `state_schema_version` 逐期升版與 `state-schema.lock.json` 的同版簽章擋建置；`build/state_schema.py` 的 preflight 改為**只印出**「持久成員版面與上一輪的差異」（仍是好用的回歸訊號），不再失敗。
2. 舊任務 FormID 的無 VMAD stub（`ESSB_MainQuest_Schema1..6_Stub`、`ESSB_MCMQuest_Schema1..6_Stub`）：第 2 期起從 ESP 移除；`quest_ids()` 固定配 `0x006000／0x006001`。
3. 「既有 FormID 一律不得變動」：改為**只報告不擋**——建置仍與前一輪快照比對並列出每一筆差異（新增／刪除／改 ID），差異本身不是失敗；`ESSB_DebugLevel = 0x000811` 的「契約」只剩 `ESSBLog.psc` 的一行 `GetFormFromFile`，改成 Property 綁定後連這條都不需要固定。
4. 「每一期都可在舊存檔上運作」：放寬；保留「每一期可獨立驗證、可回退」（每期一個 package 快照與一張探針卡，10.2）。

這解開了哪些當初為存檔相容而折衷的選型（逐項改進計畫）：
- **AME 的世代檢查**：`ESSBMark/ESSBStatus/ESSBCounter/ESSBSilence/ESSBFormRules/ESSBFormPowerEffect` 每個事件開頭的 `Controller != ESSBState.ControllerQuest()`（`ESSBMark.psc:24`、`ESSBStatus.psc:76`、`ESSBCounter.psc:14`…）是為了讓舊世代的效果實體閉嘴；每一次都是一個 `Game.GetFormFromFile` 原生呼叫加一次跨實體 `GetAlias`。沒有舊世代就沒有這件事：改為 `Quest Property Controller` 直接用（VMAD 綁定，零原生呼叫），`ESSBState.ControllerQuest()`／`Operational()` 刪除。每個印記事件少 2 個原生呼叫。
- **控制器的 `IsCurrentController()`**（`ESSBController.psc:6389-6397`）出現在幾乎每個函式開頭，同樣是世代檢查：刪除，保留 `StateBroken`／`Ready`（那是配置失敗與初始化順序，不是存檔）。round 16 A2 加在 `RefreshDivineProtection`／`RefreshAbilities`／三個 Trees 呼叫點的守衛一併簡化。
- **`ReconcileLoadedForm`／`FirstSetupDone`**（`ESSBController.psc:6866-6920`）：「新世代第一次 Setup 要收拾舊世代留下的形態與能力」的整段刪除；`Setup` 只保留無條件 `EndDeferredKill()`（round 15 指揮官補丁，防的是引擎狀態不是存檔）與一般初始化。
- **`InitBackupInts` 的 27→38 升版、`UpgradeInts`、`CopyRing`「older saves」路徑**：隨 `ESSBStatus` 整個刪除，不再需要為它們寫任何相容碼。
- **記錄身分**：第 5 節的新記錄可以**按家族連續配號**（印記一段、階梯一段、自身階一段、附傷變體一段），不必塞進 `0x0051xx` 的縫隙；被替換的 `ESSB_MarkEffect_<X>`／`ESSB_MarkSpell_<X>`／`ESSB_StatusHost*`／`ESSB_Engaged*` 直接消失，不留 stub；`NEXT_OBJECT_ID` 由生成器算。第 5 節的「建議 `0x005200–0x0053FF`」改為「生成器自行分段配號，並在建置輸出印出每段的範圍」。
- **`ESSBPlayerAlias.psc`**（v0.3 不編譯的歷史檔）：從 `src/` 刪除；`state_schema.py` 的 `SCRIPTS` 名單同步。
- **fix round 7 的核准豁免「毒／血層壽命不受持續時間滑桿影響」**（`實作紀錄.md:2838`，理由是固定桶容不下 3 倍壽命且要保留匯出布局）：引擎 DoT 沒有這個限制，`ESSB_MultDuration` 對中毒與血痕的時長照常生效——這是限制解除後撿回來的一條功能。
- **成員變數「不敢加」**：第 1 期的 `RankCacheA/B`、`CachedSyncStage`、Guard 的 `NodeBits` 等鏡射原本要付 schema 升版的代價，現在免費；第 2、3 期任何為了「不改版面」而繞路的做法（例如把新狀態塞進既有陣列的空格）一律不做，直接開新成員。
- **驗收哲學**：`FIX9`～`FIX16` 驗證器裡「舊實體被丟棄」「stub 不含 VMAD」「schema 升版剛好 +1」的斷言在第 2 期起移除；保留的是配置失敗熔斷（`BreakState`）、初始化順序（`Ready` 後才註冊事件）、以及新加的 `HITPROC／LADDER／SELF ok`。

**從 round 9–16 保留的**：`StateBroken/Ready` 守衛（執行期安全，不是存檔相容）、`StartDeferredKill` 神佑與 MCM「解除神佑保護」、九個原生防護視窗、真實時間期限（自身計時器）、`HitForm/HitSneak/HitPower` 命中事實與 `SettledDead` 去重、擊殺歸屬規則（改讀標記，語意不變）、領域三格與居民時間、化灰／復生／恐懼／瘋狂／洗淨、MCM 滑桿與預設、CSF 樹、`build/*_verify.py` 的驗證框架。**重建的**：`ESSBStatus`（刪）、`ESSBMark`（重寫）、`ESSBController` 的登記表／狀態／傷害紀錄／自身資源、`ESSBReactions`／`ESSBElem*` 的狀態讀寫介面、`build_v03.py` 的印記與狀態記錄段。

---

## 7. 什麼消失了，以及沒有別的東西依賴它（來源掃描）

`grep -c` 於 `src/*.psc`（2026-09-20）：

| 介面 | 呼叫點 | 去向 |
|---|---|---|
| `GetStack(` | Controller 13、Elem 10、Elem2 8、Elem3 8、Reactions 2、Status 3（共 44） | 全部改 `TierOf`（第 2 期第 5 項） |
| `AddStack(`／`AddStackTo(`／`SetStack(`／`ClearStack(` | 23／26／14／10 | 全部改 `Promote/SetTier/ClearLadder` |
| `RegStatus` | Controller 33 | 刪 |
| `PendingStacks` | Controller 10 | 刪 |
| `ExportInts/ImportState/ExportFloats` | Controller 3、Status 4 | 刪 |
| `SwapHosts/SaveSwapData/ReadSwapInts/ReadSwapFloats/BackupValid` | Controller 16 | 刪 |
| `StatusHostSpell/EnsureStatus` | Controller 25 | 刪 |
| `AddAstral/DetonateAstralNow` | Controller 7、Elem3 1、Reactions 1、Status 4 | 星痕引信 |
| `SetFrozen/IsFrozen` | Controller 3、Elem 1、Status 1 | 凍結 T3 存在測試 |
| `SetCatalyze/IsCatalyzed` | Controller 3、Reactions 1、Status 2 | 催毒 DoT 存在測試 |
| `SetDeathCurse/HasDeathCurse/ResolveDeathCurse` | Controller 4、Reactions 2、Status 4 | 死咒引信 |
| `SetStarLock/HasStarLock`、`SetWetLock/ReleaseWetLock/IsWet(`、`SetAirborne/GetAirborne` | 9／10／10 | 單階標記存在測試；浮空引信 |
| `BleedRemaining` | Reactions 1、Status 1 | `GetMagnitude×剩餘秒` |
| `SpreadPoison` | Controller 1、Elem3 2、Reactions 1、Status 1 | `ESSBSpread` |
| `GetSelf/AddSelf/SetSelf/ClearSelf` | Controller 17、Elem 12、Elem2 5、Guard 4、Reactions 5（第 3 期） | 自身階梯 |
| `LastDamageFor/LastDamageWasElement/NoteDamageElement/KillElementFor`、`DamageActor/DamageElement/SwapFloats`、`RegLastDamage`、`DeadElement/SettledElement`、`kill_attribution_seconds` | Controller（5617-5706、5779-5798、5800-5926）、`ESSBState.KillAttributionSeconds`、`ESSBElem2.ShouldAsh/TryKillStreak`、`ESSBElem3.OnKill` 的 `aiKillingElement` 參數 | 刪（決定 4）：死亡節點改看死時身上的效果 |

沒有任何 `.psc` 之外的東西讀這些介面（MCM 只呼叫 `RefreshRuntimeValues/RefreshTrees/RefreshAbilities/Respec*`；CSF 與 MCM JSON 只引用 GLOB／PERK／QUST）。`ESSBFormRules`、`ESSBCounter`、`ESSBSilence`、`ESSBFormPowerEffect`、`ESSBSettingsEffect` 不碰狀態容器（掃描為 0）。

---

## 8. 必須留在腳本裡的最小核心，以及「跨目標污染在結構上不可能」的不變量

**留在腳本裡的**（全部是「反應」，不是「狀態」）：
1. 印記的開印／終焉分類與反應（`ESSBMark`）。
2. 引信到期的效果（`ESSBFuse`：星痕、死咒、浮空）；過熱引爆與爆燃的消耗換算（`ESSBReactions.EndFire`、`Ctl.Overheat`，一次終焉一次腳本）。
3. 中毒 II 以上的擴散（`ESSBSpread`）。
4. 你身上的資源升階與受擊降階（Controller／Guard；第 3 期後若進入點能對施法者套 Self 法術則消失）。
5. 融斷的範圍掃描與逐目標結算（Controller，按 Z 一次）。
6. 雙印（通用樹開啟專精分支）：目標已有兩個印記時，腳本讀兩個印記的 `GetTimeElapsed()` 切掉較舊的那個——這是唯一「比較兩個效果誰先誰後」的地方。
7. DoT 每秒值與放血換算：在**套用前**寫進法術（`SetNthEffectMagnitude`），之後引擎自己跳；腳本不再每秒觸碰目標。
8. 中毒的成長（決定 1）：命中時讀目標身上這一顆效果、算新值、重套——這是唯一「命中路徑上讀目標狀態」的腳本，約 6 次原生呼叫、無狀態，且排在附傷之後（附傷本體仍由引擎先落地）。
9. 碎冰的真傷（決定 3）與風的多段觸發（決定 9）：都是「看到目標身上的效果就做一次」，無狀態。

補充不變量 **I7 共用法術只有一個寫入者**：`ESSB_PoisonSpell` 等會被改 magnitude 的 SPEL，只由 Controller 的 `PoisonApply`／`ApplyDamageRaw` 寫值並立刻套用；效果腳本一律呼叫 Controller，不自己 `SetNthEffectMagnitude`。

**不變量（違反任一條就是設計錯，不是 bug）**：
- I1 **每一筆目標狀態只存在於該目標的 ActiveMagicEffect 列表裡**：值＝該效果的 magnitude／duration／存在。腳本裡沒有任何以 slot、index、actor 為鍵的陣列或 bank 存目標狀態。
- I2 **帶腳本的效果只知道自己的目標**：`ESSBMark/ESSBFuse/ESSBSpread` 的成員只有 `Holder`（= `OnEffectStart` 的 `akTarget`）、`Ctl`、常數屬性；它們對控制器的每一次呼叫都把 `Holder` 當參數傳過去，控制器不回查任何表。
- I3 **沒有序列化**：沒有 Export／Import／Backup／Upgrade；效果換宿主的概念不存在（30 秒宿主不存在，每階自己有 duration）。
- I4 **狀態的寫入只透過套用法術**：升階＝套 `Promote{k}`，降階＝套低一階，清除＝`DispelSpell`；引擎的「驅散同關鍵字」保證同一階梯同一時間只有一階。
- I5 **讀取只透過存在測試**：命中路徑不讀任何腳本變數決定目標狀態；PERK 條件與 `HasMagicEffect` 是唯一的讀法；需要強度時讀該效果自己的 `GetMagnitude()`。
- I6 **沒有目標數上限**：容量由引擎的效果列表決定；沒有「第 9 個目標」路徑。

在這六條下，「A 目標的毒跑到 B 目標身上」需要引擎把一個 ActiveMagicEffect 掛錯目標——那是引擎 bug，不是本模組能做出來的事。

---

## 9. 設計會失去或改變什麼

逐條清單在 `元素魔戰士規劃-v0.3_alter.md` 開頭「相對 v0.3 的改動總表」（22 條，全部已定案）。實作層面另有四條，已一併定案：
1. 潛行與重擊改由引擎當下狀態判定（alter 第 18 條）；被發現的潛行揮刀也吃風的 ×3。
2. 讀檔後 `Setup` 跑完之前（約 2 秒）附傷用 ESP 預設 magnitude（雷用 R3 = 13）。
3. 中毒的成長是命中路徑上唯一的腳本讀寫（無狀態），在高負載下它會比附傷晚幾秒，但不會錯到別人身上。
4. 雷的 best-of-N 是五檔量化，期望永遠比真值低 0.3～0.8。

---

## 10. 驗收

### 10.1 離線（建置與 harness）
- `python build_v03.py` exit 0，既有每一行 ok；新增 `HITPROC ok`（第 1 期）、`LADDER ok`（第 2 期）、`SELF ok`（第 3 期）：內容見第 6 節各期。
- FormID：建置印出與前一輪快照的完整差異表（新增／刪除／改 ID／改型別），**只報告不擋**；第 1 期仍照 Astra 的範圍（6→7、stub），第 2 期起 stub 消失、schema 不再升版。
- harness（沿 `build/fix15_verify.py`／`fix16_verify.py` 的作法，直接執行 source body、mock native 邊界）：
  - 第 1 期：`RefreshProcMagnitudes` 對六個狀態序列的寫入值 = 舊 `ApplyProc` 對同狀態的值（目標側乘數設 1）；重複呼叫零次 `SetNthEffectMagnitude`；雷五檔的鏈式機率 p_j 由生成器從 P_j(N) 反算並斷言還原誤差 < 0.5%；`SyncStage` 快取 200 樣本等值；Guard 無事可做時對 `Ctl` 零呼叫。
  - 第 2 期：`PayHealthCost` 對 150／300／500 血在 0.5% 與 10% 下的扣法與 1 點底線，且 harness 斷言它不呼叫任何法術套用；`ESSBMark.OnEffectFinish` 六條路徑（刷新、被切掉＋接管元素、融斷、過期、死亡、雙印）各得正確 `reason`；風被切掉時 `WindEcho` 對火／冰／毒／聖／雷各做出 alter 2.6 說的結果；`ESSBFuse` 到期／取消／升階被驅散三種；中毒成長公式（開印 3 劑 → 命中 ×5 → 上限 10 劑、時長夾 15 秒；催毒 ×2 不改剩餘秒；死亡份額 max(R, 0.3H)×0.5 對 3 個鄰居、鏈式第二跳 ×0.5、有限敵人下必終止）；碎冰對一般／首領 20%／10% 且一次冰封只結算一次；`OnKillEvent` 對「帶神聖印記」「帶黑暗印記」「兩者」「無印記」四種屍體的行為；血潮的剩餘量計算；**用 `180126` 的 log 值做反例**：任何合法操作序列都無法讓 `TierOf` 回大於 4 的值、`HasMagicEffect(浸濕鎖)` 只有 True/False。
  - 第 3 期：同調升段命中門檻（5/15/30 ± 節點，2026-09-22 還原 v0.3 計數）、電荷／岩甲升降、Guard 受擊降階。
- 靜態：`grep` 證明 `src/*.psc` 內不再出現 `PendingStacks|BackupInts|SwapHosts|ExportInts|ImportState|RegStatus|RingSum`；沒有任何 `Int[]`／`Float[]` 成員以 actor 為鍵。

### 10.2 探針卡（每期一張，使用者開臨時測試檔跑，測完即刪）

原則：能離線用 `Skyrim.esm`／Ordinator／Phenderix 的位元組確認的不上卡；會讓後面幾期在錯誤假設上疊工的探針**提前到第 1 期**，就算它驗的是第 2、3 期的機制；每張卡五分鐘內跑完，步驟照順序、每步寫「看到什麼＝通過／不通過」與退路。每期建置附一個「探針存檔套件」：一個開好火形態、樹等級 1、除錯等級 1 的新檔（由指揮官用主控台 `coc` 到 Helgen 外做，不要求使用者操作主控台以外的東西）。

#### 第 1 期探針卡（round 18 建置）

| # | 步驟 | 通過 | 不通過 → 退路 |
|---|---|---|---|
| 1-1 | 開火形態，砍一個強盜三刀 | 每刀砍中的**同一瞬間**看到火焰衝擊與掉血數字（比第 16 輪的建置明顯早） | 沒有火焰或延遲不變 → `ESSB_P_HitProc` 沒生效：檢查 `Setup` 的 `AddPerk`、進入點條件的 GLOB 值（主控台 `GetGlobalValue ESSB_CurrentElement`） |
| 1-2 | 徒手（收起武器）打同一個強盜一拳 | 同 1-1 有火焰 | 沒有 → 拳腳不走進入點：第 2 期保留 PO3 `OnWeaponHit` 對武器型別 0 的腳本附傷（退路已在計畫，成本一段 if） |
| 1-3 | 換弓射一箭，再蹲下潛行射一箭 | 兩箭都有火焰；潛行那箭數字約 1.5 倍 | 弓沒有 → 分頁 0 `GetEquippedItemType` 條件錯：改用分頁 1 `HasKeyword(WeapTypeBow)`（原版 `TrickShot` 用法）；弩另測 |
| 1-4 | **提前探針（決定第 2 期的生成器形狀）**：本期建置附一段除錯進入點——對帶「已交戰」標記的目標再多套一顆 `ESSB_ProbeMagnitude`（固定 10 點火傷），並附一段 0x1D「Mod Spell Magnitude ×2、法術帶 `ESSB_Probe` 關鍵字」。砍第二刀 | 看到一個約 **20** 的額外數字 | 看到 **10** → 0x1D 不作用在進入點套的法術上：第 2 期把 `tier_multiplier_mode` 切成 `spell_variant`（每階一個法術版本，生成器已支援，多約 30 筆 SPEL） |
| 1-5 | **提前探針**：同一段除錯建置另附兩段條件完全相同、法術不同的 `ESSB_ProbeA`（5 點）／`ESSB_ProbeB`（7 點）。砍第三刀 | 同時看到 5 和 7 → 引擎「全部套用」；只看到 5 → 「首段即停」 | 兩者都可：把結果填進 `settings.json` 的 `lightning_roll_mode`（`additive`／`chain`），第 1 期後半的雷五檔照填的模式生成 |
| 1-6 | 打開 Ordinator 瓦希安魔法（若已啟用），記下剩餘法術數，砍 10 刀 | 數字不變 | 減少 → 進入點套用會發 `OnSpellCast`：整個原生附傷與瓦希安不相容，回報使用者決定（關閉瓦希安或回腳本 `DoCombatSpellApply`）；這是唯一沒有退路的探針 |
| 1-7 | 站在跟班旁邊砍空氣，再讓跟班挨一次敵人的攻擊 | 跟班血量不變、本模組 L1 紀錄沒有「受擊」行 | 有 → 分頁 2 的 `GetPlayerTeammate`／`IsCommandedActor` 條件沒寫進段裡 |
| 1-8 | 開 MCM 熱鍵頁，按 Numpad 2 切冰，立刻砍 | 武器光立刻變藍、那一刀是冰的衝擊 | 那一刀仍是火 → `ESSBInput` 沒先寫 GLOB；改 `RequestSwitch` 的順序 |
| 1-9 | 一刀砍死一個殘血的狼；看 L1 紀錄的 kill 行 | 出現 `element=1` 或明確為 0（兩者都可） | — 此項只記錄致死那一擊有沒有套進入點法術（第 11 節第 2 題），不擋工 |
| 1-10（選配，只有不裝 Ordinator 時需要） | 探針包加兩段優先度都是 0、條件相同、法術不同的 entry 51 | 看到哪一顆 → 同優先度的勝負規則 | 有 Ordinator（最小優先度 50）時我們的 0 永遠贏，不需要此題 |

1-4 與 1-5 已於 2026-09-22 實機完成（4.10）：0x1D 有效；一刀只套優先度最小的一段。

#### 第 2N 期探針卡（SKSE 插件）

| # | 步驟 | 通過 | 不通過 → 退路 |
|---|---|---|---|
| N-1 | 裝好 DLL，開遊戲到主選單，看 `Data/SKSE/Plugins/ElementsSpellblade.log` | 一行「version 1.5.97 ok, native hit ON」；MCM 顯示版本字串 | 沒有 log → DLL 沒被 SKSE 載入（檔名、路徑、SKSE 版本） |
| N-2 | 火形態砍三刀 | 每刀同幀火焰；`[ESSB][hit][L2]` 行出現在 DLL 的 log 而不是 Papyrus log | 沒火焰 → `ESSB_NativeHit` 為 1 但 sink 沒收到或 manifest 沒解析；log 寫哪一步失敗 |
| N-3 | 砍一刀，數附傷數字 | 只有一次（ESP 已無 entry 51 附傷段，不會雙套） | 兩次 → 生成器沒移除附傷段 |
| N-4 | MCM 關掉「原生命中」，砍一刀 | **沒有**火焰（此時本模組沒有附傷），DLL log 沒有新命中行；開回來火焰回來 | 關掉仍有火焰 → 開關沒接到 sink；開回來沒火焰 → 重新啟用路徑錯 |
| N-5 | 瓦希安魔法法術數：砍 10 刀 | 不變 | 減少 → DLL 的即時施放發了 `OnSpellCast`：改用直接套效果的替代呼叫（待查證）；沒有退路，回報使用者 |
| N-6 | 站跟班旁邊砍空氣、讓跟班挨敵人一刀 | 跟班血量不變 | 有 → DLL 的目標過濾缺同伴／受命判斷 |
| N-7 | 把 Address Library 的 `version-1-5-97-0.bin` 暫時改名，開遊戲砍一刀，改回來 | log 一行「address library missing, native hit OFF」；砍一刀沒有火焰、遊戲不崩 | 崩潰 → 版本檢查在 sink 註冊之後才做，順序錯 |

#### 第 2 期探針卡（目標狀態層）

| # | 步驟 | 通過 | 不通過 → 退路 |
|---|---|---|---|
| 2-1 | 冰形態砍同一個目標：第一刀、等 2 秒、第二刀 | 第一刀目標變藍（凍結），第二刀目標結冰（冰封）且掉一大口血（20%），冰封隨即結束 | 第二刀沒冰封 → 成熟計時效果沒被驅散（檢查 Cool 關鍵字不在驅散清單）；沒掉 20% → `ApplyTrueDamage` 沒接到 |
| 2-2 | 火形態連砍一個目標 5 秒，換冰形態再砍一刀 | 換冰那一刀看到火的爆燃數字，再看到冰的開印 | 只看到其中一個 → 餘燼機制（4.9）沒接上：看 L1 的 End 行 reason |
| 2-3 | 火形態砍一刀後離開 10 秒不打 | 8 秒左右看到一次火的終焉數字（過期） | 沒有 → `ESSBEmber.OnEffectFinish` 沒跑或被 `BurstDone` 誤擋 |
| 2-4 | 毒形態砍一個目標 6 刀，看它掉血 | 每秒掉血且越掉越快（不是固定） | 固定 → `PoisonApply` 沒有讀舊值重套 |
| 2-5 | 讓 2-4 那個目標毒死，旁邊站兩個敵人 | 兩個都開始掉血（綠色毒效果） | 沒有 → `PoisonDeathSpread` 的資格過濾或 `MaxHealthAtStart` 為 0 |
| 2-6 | 神聖形態砍一個目標 3 刀（每刀間隔 2 秒），看自己的武器光 | 武器光三次逐漸變亮，第三刀起每刀多一個聖光數字 | 沒變亮 → 聖佑推進在 `OnWeaponHit` 的「目標帶神聖印記」判斷錯；沒有聖光數字 → III 的段條件 |
| 2-7 | 神聖形態砍死一個亡靈（Helgen 外用主控台放一隻） | 屍體化灰 | 沒有 → `OnActorKilled` 當下 `HasMagicEffectWithKeyword` 讀不到印記：啟用退路（命中時記 `HitHadDivine/HitHadDark` 兩個命中事實，擊殺時用它） |
| 2-8 | 火形態砍到白熱（約 6 秒），站在兩個敵人旁邊 4 秒不砍，再看自己的血 | 兩個敵人每秒掉血、身上出現火印記；自己每秒掉一點血；4 秒後（引信到期）自己掉 10% 且兩個敵人各爆一次 | 敵人沒掉血 → 披風關聯法術的 `IsHostileToActor` 條件把非戰鬥中的敵人排除（預期行為）或半徑單位錯（改 magnitude）；自己掉血是「傷害數字」而不是靜靜減少 → 代價路徑接錯 |
| 2-9 | 在 2-8 的白熱期間站到跟班旁邊 | 跟班血量不變 | 有 → 453／700 條件缺 |
| 2-10 | 風形態砍一刀，換冰形態砍一刀 | 換冰那一刀目標直接冰封（N=2：凍結＋冰封） | 只到凍結 → `WindEcho` 的 `Promote` 沒繞過成熟等待 |

#### 第 3 期探針卡（自身資源與同調）

| # | 步驟 | 通過 | 不通過 → 退路 |
|---|---|---|---|
| 3-1 | 雷形態連砍 12 秒，看附傷數字的分布 | 前幾刀有 3～8 的小數字，後段幾乎都 18／23 | 分布不變 → 電荷階條件段（分頁 0 `HasMagicEffect`）沒生效 |
| 3-2 | 任一形態連砍到 5、15、30 刀，看武器光〔2026-09-22 還原 v0.3：同調用命中計數，不再是秒數〕 | 第 5、15、30 刀左右各亮一檔 | 不亮 → 同調 magnitude 計數沒寫入 |
| 3-3 | 土形態砍 3 刀後挨一刀 | 護甲值（主控台 `GetAV DamageResist`）三段上升後掉一段 | — |
| 3-4 | 若第 1 期 1-5 是「全部套用」：本期附一段對施法者套 Self 法術的 0x33 除錯段，砍一刀看自己身上有沒有效果 | 有 → 自身階梯可搬到引擎（第 4 期的清理項） | 沒有 → 維持腳本推進（預設） |

#### 排到最後一次驗收的（不擋任何一期）
`SetNthEffectMagnitude` 是否進存檔（每次載入都重寫，無關）；披風半徑的實際公尺數（調 magnitude）；`GetMagnitude()` 對 DoT 的回傳單位（2-4 一併看得出來）；Papyrus log 的 suspended-stack dump 是否還含我們的事件（最後一輪 smoke）；MCM 每一頁的文字與預設值。

## 11. 從檔案無法確認的事（低信心項目），以及每一項的處置

| # | 假設 | 信心 | 處置 |
|---|---|---|---|
| 1 | 同一進入點多段同時成立時的行為 | **已測（2026-09-22）**：一刀只套優先度最小的一段，跨 perk 亦然 | 第 2 期改為單段多效果法術（4.10）；雷五檔以優先度排序即鏈式；同優先度平手未測（選配探針 1-10） |
| 2 | 致死那一擊引擎是否仍套用進入點法術 | low | 探針 1-9 只記錄；兩種結果都是已接受的行為 |
| 3 | 進入點套用是否發 Papyrus `OnSpellCast`（瓦希安） | medium（Ordinator 自身 129 段與瓦希安共存） | 第 1 期探針 1-6；**唯一沒有退路的假設**，失敗就回報使用者 |
| 4 | 0x1D「Mod Spell Magnitude」對進入點套用的法術生效 | **已測（2026-09-22）**：乾淨翻倍 | `tier_multiplier_mode = entry` 寫死，`spell_variant` 路徑可刪 |
| 5 | `GetEquippedItemType(1)` 對弩回 12 | medium | 探針 1-3；退路分頁 1 `HasKeyword(WeapTypeBow)` |
| 14 | 效果層條件對 entry 51 套用的法術逐效果評估 | high（Ordinator 12 顆 entry 51 目標法術就是這樣寫的，本機位元組實測） | 第 2 期探針 2-1／2-2 順帶驗證 |
| 15 | 同優先度平手規則 | **已測**：先加到角色身上的 perk 贏 | 甲案已不採用；紀錄留在 `build/entry51-compat-audit.md` |
| 16 | CommonLib 的命中事件、即時施放、目標效果查詢的 API 名稱與簽名；SKSE 1.5.97 插件匯出；建置相依 | 待查證（4.11 的表；網路權限已給） | Astra 寫 `build/native-verification.md`，併回 4.11；查不到沒有退路，回報使用者 |
| 17 | DLL 的即時施放是否發 `OnSpellCast` | medium（與 `DoCombatSpellApply` 同一條路） | 探針 N-5 |
| 6 | Dispel with Keywords 對階梯生效 | 已消除：階梯 MGEF 改為原型 0（Oakflesh 形狀），是原版用例 | — |
| 7 | `OnEffectFinish` 與新效果加入的順序 | 已消除：餘燼機制（4.9）不依賴順序 | — |
| 8 | `HasMagicEffect` 在 `OnActorKilled` 當下對屍體可讀（No Death Dispel） | medium（round 15 已依賴） | 探針 2-7；退路：命中事實 `HitHadDivine/HitHadDark` |
| 9 | `SetNthEffectMagnitude` 不進存檔 | medium | 無關：每次載入重寫 |
| 10 | 0x33 對 Self 傳遞法術是否套在施法者身上 | low | 探針 3-4，只影響是否把自身階梯也搬到引擎（預設腳本） |
| 11 | `GetMagnitude()` 對值修正 DoT 回每秒值；`GetBaseActorValue("Health")` 對剛死目標可讀 | medium | 探針 2-4／2-5；`MaxHealthAtStart` 在 `OnEffectStart` 先存 |
| 12 | 披風 magnitude 的單位；`IsHostileToActor` 參數 0 的語意 | medium（原版就這樣寫） | 探針 2-8；調 magnitude |
| 13 | `180126` 匯入的位元組究竟來自哪一步 | — | 第 2 期讓這個問題失去意義，不查 |

## 12. 不論分期都該做的便宜修法（與 round 17 重疊者標 ★）

| # | 位置 | 現況 | 修法 |
|---|---|---|---|
| ★1 | `ESSBGuard.psc:75-89` | 每次受擊 4 次跨實體呼叫後才決定要不要做事 | 第 6 節第 1 期第 3 項 |
| ★2 | `ESSBController.psc:3342`（`SyncStage` → `ESSBNodes.SyncThresholdScale` → Trees） | 每次讀同調段跨到 Trees 兩次 | 快取 `CachedSyncStage`，在 `AddSync/SwitchForm/CloseForm/RefreshTrees/RefreshRuntimeValues` 與形態持有跨過 60 秒時重算 |
| ★3 | `ESSBNodes.Rank/Br` → `ESSBTrees.MainRankInternal/BranchInternal` | 命中路徑每次節點查詢都跨到 Trees | 鏡射到 Controller |
| 4 | `ESSBController.psc:3310-3312` | 三段同調每擊呼叫 `RefreshDivineProtection` | 刪，改由 `OnSyncStage` |
| 5 | `ESSBController.psc:1590` | `ResolveHitWeaponType` 在 `Enabled` 檢查之前 | 交換順序 |
| 6 | `build_v03.py:766` 與 875-953 | 條件函式 693 用在攻擊者分頁 | 改 699（`HasMagicEffectKeyword`），並在實作紀錄記錄決定 44 的更正 |
| 7 | `build_v03.py` 決定 61 的註解 | 「攻擊類進入點讀不到目標」 | 更正為「分頁 2 是目標」，解鎖 5.7 御風／空中追擊的武器傷害放大 |

**剩餘每擊預算（第 2 期後，Controller `OnWeaponHit` 一次有效形態命中）**：跨實體呼叫 ≤ 1（`Trees.AwardInternal`），原生呼叫 ≤ 15（自身階梯的存在測試與一次 `DoCombatSpellApply`、命中事實），`SetNthEffectMagnitude` 0 次，對目標的狀態讀寫 0 次（全在引擎）。受擊 `OnHitEx` 無事可做時 2–3 個 GLOB 讀取、0 跨實體。這兩個數字要進 `build/papyrus_harness.py` 的表並斷言上限。
