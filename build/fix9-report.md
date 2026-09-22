## FIX9 — 舊存檔 schema 換代與 Papyrus flood HOTFIX

### 結果與交付

- 交付：`package/Elements Spellblade/`。親自執行 `python build_v03.py`，exit 0；完整輸出：`build/fix9-build.log`。未部署，未寫入 MO2 或 SkyrimSE，未存取網路；未進遊戲實測。
- `READBACK ok: masters=['Skyrim.esm'] records=3915 manifest=3915`；`CSF ok` 13/13；`DELIVERY ok`、`LAYOUT ok`、`DOT ok`、`MCM ok`、`FIX7 ok`、`FIX8 ok`、新增 `SCHEMA ok`／`FIX9 ok`；`PLAN COVERAGE` 542 rows、0 unmapped。既有「穩步」進入點的 1 項 DEFERRED 保留。
- 19 支打包腳本全部 exit_code 0（`build/v03-compile-results.json`）。所有既有來源維持 UTF-8／BOM 與原有 LF 或 CRLF；本段以 bytes append 加入，既有紀錄（包含原本混合換行）完整保留。

### A：陣列判斷與初始化

- `src/*.psc` 全掃描：原有 63 處陣列 `== None` 全改成 `!arrayVar`；沒有留下陣列 `!= None`。`InitFixState`／`InitRegistry` 各有單一成功旗標 `FixInitialised`／`RegistryInitialised`，成功後直接返回；`InitTables`、Guard 陣列亦有旗標，不再於每個 tick 重測／重建所有陣列。
- 配置後立即檢查，失敗呼叫 `BreakState()`；`StateBroken` 永久鎖住該 instance，先關閉 Ready、取消更新／武器事件，再顯示一次 MessageBox。沒有重試／清除 latch 的路徑。OnInit、OnPlayerLoadGame、OnUpdate、排程、hit、kill、mark/status callbacks、form powers、MCM／技能樹入口均受此狀態限制；所有 init 呼叫後也立即檢查，不會繼續索引失敗陣列。
- 訊息指引玩家退出遊戲、安裝「已提升 state_schema_version 並重新建置」的完整更新包後重載原存檔；無需清存檔。這是維護者的建置版本，不是讓玩家修改 JSON 就能修復。

### B：可延續的 save schema

`settings.json` 新增 `state_schema_version: 2`。未版本化的 rounds 1–8 視為 schema 1。只有兩個 QUST 使用 schema 配號，其他 record 身分固定。

| EDID | schema 1 / pre-fix9 ID | schema 2 ID／用途 |
|---|---|---|
| ESSB_MainQuest | 000800 | 006000，新 Player alias 0，掛 ESSBController／ESSBTrees／ESSBGuard |
| ESSB_MCMQuest | 00515B | 006001，新 ESSBMCM 與 SKI_PlayerLoadGameAlias |
| ESSB_MainQuest_Schema1_Stub | 無此 EDID | 000800，保留舊 form，無 VMAD／aliases／start-game-enabled |
| ESSB_MCMQuest_Schema1_Stub | 無此 EDID | 00515B，同上 |

- `build/state_schema.py` 的 `quest_ids(v)`：v=1 使用原 ID；v>=2 從 006000 起每代配置 2 個 ID；所有較舊版本逐代生成 stub，從不回收。schema 3 的 active IDs 為 006002／006003，schema 1、2 均留下 stub。專用範圍 006000–006FFF，超界直接失敗；HEDR `next_object_id` 隨 active IDs 推進，目前 006002。
- MCM 也換代：它本身保存 Quest instance、繼承 MCM/SkyUI 狀態，且 `Controller` 可能指向舊主 Quest；只換主 Quest 不足。回讀盤點只有這兩個 QUST 承載腳本。
- `own(ID_QUEST)`、`own(ID_MCM_QUEST)` 統一使用動態配號。驗證器真正解析每個 VMAD 的 scalar／array object refs 及 alias fragment refs，確認沒有指向任何 retired quest；SEQ 只有兩個新 active IDs。MCM JSON 的 41 個參照可解析，3 個動作皆指向新 MCM Quest。13 個 CSF 使用既有 GLOB／PERK 身分，不帶舊 Quest ID。
- 與 `.codex/pre-fix9-snapshot/v03-formids.json` 比對，3913 筆原身分中只有上述 2 個 active QUST 改 ID，新增 EDID 只有上述 2 個 stub；其餘 3911 筆完全相同。全部 150 GLOB、3226 PERK、120 SPEL、134 MGEF ID 不變，`ESSB_DebugLevel = 0x000811`。
- 離線成立的依據：新 QUST FormID 會取得全新、型別完整的 script／alias instance；舊 FormID 留下無 attachment 的 stub，依本輪提供的 Papyrus 存檔行為，舊 instance 在載入時被丟棄，可能出現一次 orphan warning。ESP 結構、參照及程式安全邊界已回讀／執行驗證；實際引擎丟棄行為沒有冒稱為已遊戲實測。

### schema 維護規則（必要）

1. **任何 persisted script 新增、移除、改名或改型別 member variable／有儲存狀態的 Property，都必須把 `state_schema_version` 加 1。** 陣列和 scalar 都算；改繼承型別、增刪 instance script 也算。僅函式內 local variable、函式邏輯、文字或預設數值變動，無 layout 變動時不必 bump。改變既有狀態語意或需要拋棄舊戰鬥狀態時，即使 signature 相同也應 bump。
2. `state-schema.lock.json` 是需隨源碼一起保存／提交的 schema 資產，保存版本、完整 signature、SHA-256、配號及歷史；不要刪除或手動改 hash 來繞過版本檢查。建置最開始執行 preflight，同版本 signature 不同會立即失敗，尚未產生 ESP／PEX。降版、跳號、lock 內容不一致也失敗。
3. 版本恰好 +1 時，建置將前一版摘要移入 history，更新 lock 並生成新 active quests 與所有舊 stub。每次已發布版本都必須保留歷史；不可把版本改回去重用 Quest IDs。若建置中途失敗而再修改 layout，需繼續 bump，或在**尚未發布**的同一輪開發中先還原上一個已發布 lock，再重新產生本輪 lock；不可改已發布版本的 signature。
4. signature 涵蓋本包 11 支有 instance 的腳本，另包含本機 3 個 MCM/SkyUI 編譯祖先介面；Hidden 全域函式腳本無 instance，locals 不納入。外部 MCMHelper/SkyUI 的真實 PEX 未被此編譯介面 hash 取代。
5. MGEF 的 ID 保持固定。短期 `ESSBStatus`／`ESSBMark`／`ESSBCounter`／`ESSBSilence` 以保存的 `Controller` Quest 與生成的 `ESSBState.ControllerQuest()` 比較世代；舊效果直接停止處理，等待自然到期。`ESSBSilence` 的舊 instance 沒有 Controller，因此安全返回。今後新增其他持久效果也必須保留這個世代入口；永續效果必須在新 Setup 重掛。`ESSBFormRules` 已如此處理。

### C：其他錯誤及判定界線

- 摘錄 histogram 的總計是 `Cannot create an array into a non-array variable` 181993 次；使用者另指出其中 InitFixState 約 105k。`Cannot access an element of a None array` 33348 次，以及 InDomain／DomainFlag／TickTimers 的無效讀取，是配置失敗後繼續執行的下游後果；schema 換代及 init 後返回共同封堵。
- `Cannot cast from None to ...[]` 是 A 的獨立根因，不能只靠換代修掉。
- `value()`／GetValue／GetValueInt／SetValue 的 None 接收物件符合舊 instance 缺少新 property 的問題；新 VMAD 重新綁定，Setup 在使用前驗證所有必要 GlobalVariable、Spell、Trees 與陣列／object 陣列元素。缺少必要 binding 也直接熔斷。摘錄只提供首 400 筆 ESSB 命中行與 aggregate histogram，未提供每個錯誤旁的完整 stack，因此不能宣稱 101 次 `value()` 都已逐筆定位到相同 property。
- 額外補上 `ESSBElem.Shatter` 的空控制器／空 target 提早返回，及 IsDead 前 target 檢查；Status frozen FX 與 update 路徑保留／補強 Holder 檢查。`ESSBCounter.OnEffectFinish` 不再於 AME native binding 已拆除後呼叫 UnregisterForAnimationEvent，FormRules／Silence 的 finish 同樣交由引擎解除註冊。
- histogram 也含 `newsparks`、`FloraHarvestScript`、invalid sound、對話等錯誤；在現有摘錄無法配對 ESSB stack 的項目不臆測為本模組，也未修改其他模組。本包没有 Sound.StopInstance／IsInDialogueWithPlayer 呼叫。

### D：保留進度與載入一致性

- 新 Quest 的第一次成功 Setup 才執行 `ReconcileLoadedForm()`：FormActive／CurrentElement／Sync 及戰鬥狀態鏡射歸零、移除所有 11 個 FormAbilities，移除旧 FormRulesAbility 再加回以建立新 AME，移除舊岩甲 buff；RefreshAbilities 依保留的 perks／新非形態狀態重算條件能力。
- SettingsPower／11 個 FormPowers 使用 HasSpell 判斷，只補缺少項；BaseRulesPerk 也僅在缺少時加入。舊 SPEL／MGEF IDs 全保留；form power cast 使用生成的 current Quest resolver。技能樹等級、Ratio、perk points、洗點冷卻、已購 perks 與設定 GLOB 不重設。
- `FirstSetupDone` 隨新 instance 保存；同 schema 後續讀檔不會再次強制關閉合法的現行形態，重複 Setup 也不反覆重掛隱藏能力。

### 離線驗證

- `build/fix9-runtime-check.json`：直接執行實際 Papyrus 函式內容（native 邊界 mock），逐一讓 67 個 Controller、6 個 Trees、2 個 Guard、4 個 Status 陣列的賦值失敗，共 **79** 例；每例最多一次配置失敗、一次訊息，後續 init/load/update/hit/kill/form/回呼不重試。另測 5 個必要 VMAD binding 缺失。
- 初始化成功後以「讀取 truthiness 就拋錯」的陣列替身驗證快路徑；40 次重複 Setup／init 不重建陣列、不重複增加 powers、不重掛 FormRules，保留 progression/settings。舊 AME 以任何 orphan 物件存取都拋錯的替身驗證先行隔離。
- schema 新增／移除／retype、降版、跳號反例失敗；單純增加 local 變數不影響 signature；下一版配號及 stub 累積經檢查。ESP 有 3915 個唯一 records，無新 masters。
- 原 FIX3–FIX8 驗證只針對兩個 Quest schema 例外、入口 safety guard 與新增的 resolver 調整，仍檢查非 Quest 身分、既有序列化 layout／公式／entry points／upkeep／CSF。原 FIX8 scope snapshot 早於使用者既有的部署備份、pre-fix9 snapshot 和 campaign ledger 變動；這些既存檔案改用本輪 protected hash 固定比對，未寫入 `.strategic-advance/**`。
- `build/fix9-protected-hashes.json` 驗證禁止修改的檔案未在本輪後續工作中變動；`實作紀錄.md` 僅附加。本包未加入 Utility.Wait 或 RegisterForUpdate。

### 剩餘 None 比較（全部是非陣列）

執行 `rg -n '[A-Za-z0-9_]+ (==|!=) None' src -g '*.psc'`（等價於指定 grep；PowerShell 不展開 src/*.psc 給 rg）。只剩 6 行、8 個 scalar object 比較：

| 檔案／行 | 左側變數 | 宣告型別／用途 |
|---|---|---|
| ESSBController.psc:1301、1304 | akProjectile | Projectile 事件參數 |
| ESSBGuard.psc:75、98 | akProjectile | Projectile 事件參數 |
| ESSBGuard.psc:75 | sourceSpell | Spell，來源施法判斷 |
| ESSBPlayerAlias.psc:34 | akProjectile | Projectile；歷史來源，v0.3 不編譯／不附掛 |
| ESSBTrees.psc:449 | player、branch | Actor、Perk，HasPerk 前物件判斷 |

### 遊戲內驗證界線

退出遊戲後安裝完整 `package/Elements Spellblade/`（包含 ESP、19 PEX、SEQ、MCM/CSF），直接載入原有存檔，不需 clean-save。預期首次新 schema 關閉舊形態且保留進度，powers 能再次開啟。若需要 [ESSB] gameplay 訊息，可暫將 MCM 除錯等級設為 1 後重載；預設仍為 0。須以新一輪 Papyrus log 確認沒有持續刷錯，才能宣稱實際遊戲問題已解除。
