# Round 10 完成報告

已完成 A–D 修正與離線驗收；`python build_v03.py` exit code **0**。沒有連網、沒有部署、沒有寫入 MO2 或 SkyrimSE；遊戲內行為仍需下一次啟動驗證。

## 證據校正與根因

輸入 `.codex/smoke3-essb-events.log` 包含主事件區與後接的錯誤周邊 context，後段會重複前段的事件。以第一筆 stack 行為分界，主區為 **1479** 行 [ESSB]（不是摘要中的 1423）；主區 **182 kill / 91 個 victim，每個恰好兩次**、**73 ash**。全檔計入重複 context 是 **85 ash**，不能把它當成 85 個獨立化灰事件。

A：指揮者的 sticky-global 分析成立，而且還漏了真實傷害與放血路徑。`ApplyDamageRaw` 在 native 傷害後寫全域 `LastDamageElement`；`ApplyProc`、`ApplyTrueDamage`、`ApplyBleedDrain` 沒更新。`Judge` 與神聖處決還額外寫 7。全域既不帶 victim，也不在切換或非致死傷害時失效。讀者 `ShouldAsh` 與亡者歸來會借用另一名死者或另一個時段的值。主區行 523–525 更有 `element=0` 的死者 `237537` 仍被記錄化灰，直接排除「只是黑暗顯示標籤錯誤」。

B：不是加大去重環就能處理的問題。原碼只有 `ESSBGuard.OnActorKilled` 呼叫 `OnKillEvent`；`SettledDead` 只在初始化配置與 claim 處寫入，沒有每 tick 清空。錯誤區行 2623–2631 等明確出現舊 `FC000800` 的 `<nullptr alias>` controller 在 `OnSyncStage`、`AddSync`、`ArmUpdate` 執行；也能找到新 `FC006000` 的 alias stack。舊 quest 被改為 inert stub 並不保證存檔內舊 Papyrus 實例立即消失。兩個實例各有自己的去重陣列，會各自接受一次同一死亡事件；實際來源雙實例回歸重現此結果。原摘要「沒有我們的 Papyrus stack 錯誤」不成立。既有 log 未附 controller ID 的 kill 行，無法把每一行個別指定給某一個實例；上述是由共存 stack、呼叫／寫入路徑與雙實例重現交叉確認的根因。

C：`chosen.Play(player)` 不接收 handle，卻播放借來的持續音。讀回 SNDR 的 `LNAM[1]`：10 個 FormActive 為 `0x08` Loop，Astral 為 `0x10` Envelope Fast；DrawSheathe 9 個為 Envelope Fast，Earth/Water 已是 0。格式來源為本機 `vendor/wbDefinitionsTES5.pas` 行 9864–9873。規劃 2.12 要開／切形態的一次事件音，因此採用授權的 **記錄修正替代方案**。

D：規劃 5.1 標題為「無元素（未開形態時的所有武器）」；5.2 明確是「任一形態啟用時」。反噬屬 5.1 破魔，應在有形態時停用。原 Guard 在檢查 FormActive 之前就處理反噬／反擊／破護，沒有共同的形態門檻。

## 實作

- **A**：移除全域 `LastDamageElement`。新增 `RegLastDamage[8]`，加 `DamageActor[128]`／`DamageElement[128]`／`DamageNext`，後援以 Actor 身分比對，支援未登記目標與登記槽被清除後的死亡回呼；無記錄回傳 0，絕不使用當前形態猜測。`OccupySlot` 承接同一 Actor 的後援，`ClearSlot` 清掉該槽；後援滿時覆寫最舊者，失去證據會保守拒絕元素限定效果，不會借用其他 victim。`ApplyTrackedDamage` 在即時 Contact/Self 傷害套用前寫目標元素，目標存活則清回 0；已死亡／Health <= 0 的目標不再覆寫。這使一次非致死神聖命中不會把後來的物理擊殺誤判成神聖。`OnKillEvent` 在派發前把 killingElement 存為區域變數，再交給化灰與亡者歸來；擊殺連鎖對其他目標造成神聖傷害也不會污染它。
- **寫入路徑**：`ApplyProc`（普攻、重擊、額外 proc）、`ApplyDamageRaw`（所有經 ApplyDamage 進來的反應／終焉／領域／元素 DOT）、`Execute`（使用指定元素）、`ApplyTrueDamage`（0，非元素真傷）、`ApplyUtil` 的 index 7（6，放血）都走 `ApplyTrackedDamage`。其他回復／削魔／控制／印記法術不寫致死元素。移除 ESSBElem2/3 的三處額外 NoteDamageElement。`ShouldAsh` 保留規劃明訂的「淨土」例外，但必須實際擁有分支、FormActive=1、CurrentElement=7、SyncStage>=3；不能以死者舊印記當作目前神聖形態。
- **B**：`IsCurrentController` 以 `ESSBState.ControllerQuest().GetAlias(0)` 和 Self 比較，先核對身分，完全不對舊 alias 呼叫 GetOwningQuest。`IsOperational`、初始化、load/update、排程及陣列前置檢查均拒絕舊實例；Guard/Trees 的入口與舊 MCM bridge 同樣拒絕舊世代。保留既有 claim-before-dispatch 的 8 格去重環，已處理 victim 的即時重送／巢狀重送都在任何 on-kill 效果之前返回；雙實例只允許目前實例派發。沒有修改玩家 GLOB 進度、點數或已取得 perk，也不倒扣舊版本可能重複給過的點數。
- **C**：`build_v03.py` 複製 FX 後，僅把 FormActive／DrawSheathe 的 `SNDR.LNAM[1]` 正規化成 0（None）。22 筆中實際改動 20 筆；其他 bytes、FormID、素材音檔保持不變。55 個 family descriptors 最終全是明確單次播放。此方案不建立持續 sound instance，關閉、切換、讀檔、StateBroken 都沒有需清理的無限 instance；程式沒有 `StopInstance`，也就沒有重複 stop 無效 handle 的路徑。它不是「追蹤 instance」方案。
- **D**：在 `ESSBNodes.Rank`／`Br` 統一限制 tree 11 的 route 0/1：FormActive=1 時回 0/False。因此反噬、反擊、破護、反咒、無魔、逆流與相關純武藝／破魔讀值都遵守門檻；未擁有分支仍為 False。清除開形態時的 RiposteLeft，移除只在有形態 proc 路徑使用它的錯置加成。route 2 融斷保留：規劃特別要求關閉、再開、餘燼、連斷、雙斷等跨狀態過渡，不能一刀封鎖。沒有調整數值係數或 branch 購買條件。另外在破護的引擎 PERK 增加 `FormActive=0` CTDA，避免無形態取得的 2 秒視窗在開形態後仍生效；ESP 回讀另驗證此條件。

## Play 與領域／光環聲音稽核

| 來源 | 實際播放途徑 | 結果 |
|---|---|---|
| FormActive（11） | PlayFormSound → Sound.Play | 改成單次 |
| DrawSheathe（11） | PlayFormSound → Sound.Play | 改成單次；Earth/Water 原本已是單次 |
| Release（11） | PlayFormSound 與引擎 FX | 原本 LNAM[1]=0，保留 |
| Charge（11） | PlayFormSound、印記 MGEF SNDD | 原本 LNAM[1]=0，保留 |
| OnHit（11） | 附傷 MGEF SNDD，引擎播放 | 原本 LNAM[1]=0，保留 |
| ESSBStatus.FrozenShader.Play | EffectShader，不是 Sound | 已有 FrozenShader.Stop(Holder)，保留 |
| 光環／領域的 EFSH ambient sound | 引擎持有，隨能力移除、效果期限、Shader.Stop 結束 | 沒有額外裸 Sound.Play；不是遺失 handle 的來源 |

`src/*.psc` 實際只有 `chosen.Play(player)` 這一處 Sound.Play。`src/menu_paging.psc.fragment` 另有不在 SCRIPTS 編譯／交付清單的舊 `ZZSound_SpellLearn.Play` 片段，未修改，也不會進入此包。借用光環 shader 指向 FormActive 的 ambient sound 也會吃到同一份單次 descriptor 修正；其他 EFSH ambient 原版／借用音由引擎效果生命週期持有，沒有新增 Papyrus handle。

## Schema 與 FormID

新增／移除持久成員依 round 9 規則把 `state_schema_version` **2 → 3**，由 schema preflight 正式更新 lock 與 history，沒有手改同版本的 signature hash。

| 記錄 | round 9 | round 10 |
|---|---|---|
| ESSB_MainQuest | 0x006000 | 0x006002 |
| ESSB_MCMQuest | 0x006001 | 0x006003 |
| ESSB_MainQuest_Schema2_Stub | 新增 | 0x006000 |
| ESSB_MCMQuest_Schema2_Stub | 新增 | 0x006001 |
| ESSB_DebugLevel | 0x000811 | 0x000811 |

對 `.codex/pre-fix10-snapshot/v03-formids.json` 的逐記錄比較：只有上述兩個現行 quest 改 ID，新增兩個 Schema2 stub；先前 Schema1 stub 保留。其餘所有既有記錄 ID／型別／metadata 不變。VMAD、SEQ、MCM 參照已跟隨新世代。

## 離線回歸與驗收

`build/fix10_verify.py` 執行實際 Papyrus 函式內容；native 呼叫用明確 mock，不宣稱模擬 Skyrim VM 排程。A/B/D 使用 `.codex/pre-fix10-snapshot/src`；C 使用修正前完整 ESP 備份 `build/fix10-before/Elements Spellblade.esp`。全部先驗證舊版必須失敗，再驗證現版通過。

| 缺陷 | 舊版失敗 | 新版通過案例 |
|---|---|---|
| A | another victim inherited divine damage | 不同 victim、神聖非致死後物理擊殺、真傷／放血、已死目標不覆寫、8 槽及後援／eviction／reuse、切形態、on-kill AoE、淨土正反例 |
| B | elem/elem2/elem3/noform 各派發 2 次 | 兩個 controller 各收兩次僅派發一次、巢狀重送、13 名死者、orphan 初始化/load/update/排程/命中/XP/Guard 不呼叫 native |
| C | FormActive_Fire LNAM=01080000 | 55 筆 family 全單次；20 筆變更僅限指定 byte，所有其他 SOUN/SNDR 欄位不變 |
| D | backlash active while form is active | Rank/Br 形態開關、owned/unowned、實際 Guard.OnHitEx 反噬，以及融斷 route 保留 |

完整 `python build_v03.py` **exit 0**：READBACK masters=['Skyrim.esm']、records=manifest=3917；19 scripts 全 0 errors；CSF 13/13；DELIVERY、LAYOUT、DOT、MCM、SCHEMA、FIX7/FIX8/FIX9/FIX10 全部 ok；PLAN COVERAGE 542 rows、0 unmapped。既有「穩步」DEFERRED 1 保留，沒有新增規劃偏離。FIX9 額外陣列故障注入總數為 82，仍一次 latch、無重試刷屏。

只針對新介面更新既有驗證 helper：FIX9 的版本門檻測試改用 lock 目前版本及相鄰版本、fixture 指向 canonical alias；FIX6 公式 mock 補上新傷害 wrapper 所需 native 邊界；FIX8 精確來源比較略去身分 guard；Papyrus harness 增加 Spell cast。沒有跳過既有測試或改寫預期平衡數值。

編碼／換行檢查通過。`build_v03.py` 仍是 CRLF；`實作紀錄.md` 原有混合換行內容逐 byte 保留，只在尾端追加。未對 `.strategic-advance/**` 做 hash 斷言或修改。

輸出：`package/Elements Spellblade/`；可直接匯入的壓縮包：`build/Elements-Spellblade-fix10.zip`；完整 build log：`build/fix10-build.log`；機器可讀驗證：`build/fix10-check.json`；差異檔：`build/fix10.patch`。

**驗證界線**：未在遊戲內測試。即時傷害前後的存活判定依賴現有 Contact/Self、無持續傷害 duration 的 native delivery；離線測試驗證的是該 native 邊界下的來源邏輯，不能替代遊戲引擎時序驗證。已丟棄 handle 的舊版音效無法由新程式追溯取得；本次不操作仍在執行的遊戲。完整退出遊戲後再使用新包，才能驗證新記錄與新世代腳本。既有存檔中已被錯誤化灰／MagicNoReanimate 的屍體不做回復，避免修改既有世界資料。
