
## Round 18 第 1 期完成實作（第三次接續；離線驗收）

### 範圍、裁定與不可變資料

承接使用者的 difference-patch 及 zero-GetStack 裁定，不重建 `pre-fix18-snapshot`，不覆寫兩次 preflight。採用 standing authority 的事項只涉及驗收表示法：

1. **零讀取**限定 Controller-local Rank/Br 可排除「任何目標倍率可能性」。火熱度 +8%/層與聖印基礎 +20% 都不需購買節點，故火/聖即使零節點仍須原 `GetStack`；其他九元素在沒有相關節點時零跨腳本、零 GetStack。持有資格但倍率最後為零的情況照舊 lazy Tick，差額 <=0 不寫入、不施法。未使用 ExportInts 替代讀目標。
2. **雷真值表**的「恰好一段」指 chain 的第一個成功選擇；五段原始隨機條件在某些 RNG 值本來就會重疊，不能同時要求任意 RNG 下原始條件互斥。固定 RNG=99 驗完整 1536 個攻擊/血位狀態的唯一路由；另依 0..99 整數量化反算五個 first-success 機率，絕對誤差 <0.5%。設定 `lightning_roll_mode` 保留 `chain`/`additive` 兩種生成方式；是否第一段即停列實機探針，沒有用其他模組的存在冒充已證明執行語意。
3. **等值參考**：非雷使用規劃明定平均 B，雷差額使用 N=1 的期望 13；血附傷使用 alter 核准四區間及反轉，保留血怒中血位 +15%。這些本期明定的表示近似不與舊隨機單次抽樣/連續血曲線作逐次等值宣稱。其他倍率和狀態沿用舊函式執行；血的吸血曲線不改。
4. **探針包**：文件要求的「已開新存檔」會越過本輪不得寫遊戲/不執行遊戲的權限，交付可選離線 probe ESP 與主控台卡，不捏造存檔或實測。兩個提前探針使用可分別加卸的 perk，移除依賴正式已交戰標記的前置條件，避免正式 74 段的 first-success 影響被測樣本。正式 ESP 不帶額外 probe 傷害。此安排只隔離驗收機制，不碰正式玩法。
5. **致死刀與光效的驗收邊界**：`NoteDamageElement` 在有效且存活的元素命中不依賴差額必定執行，並記 real-time 傷害時間；已死目標仍走 rounds 14–16 的先前凍結事實與 once-only 結算，不為追認引擎傷害而覆寫屍體歸屬（§10 探針 1-9 本來允許明確 element=0）。§4.4 已明定能力/武器光仍可能因 Controller 晚到；下一刀元素讀 GLOB 的驗收與武器光亮起時間分開記錄。

`ESSBStatus.psc`、`ESSBMark.psc`、`ESSBElem.psc`、`ESSBElem2.psc`、`ESSBElem3.psc`、`ESSBReactions.psc` 對 pre-fix18 逐位元組不變，沒有引入第 2 期階梯、餘燼標記或火披風。FIX8 whitelist/content-hash 機制保留；驗證新增 EDID 用精確集合，不用整段 FormID 豁免。既有測試與新表示不相容之處只改其邊界：例如原雷兩 effect 增為原傷害/削魔兩 effect 加已交戰第三 effect，原 `AddSelf` 逐字比對扣除新增快取刷新三行後仍需完全相同。

### 第 1–6 項產物

- 原生 `ESSB_P_HitProc` 共 74 段：EP 51、Select Spell、目標分頁友軍/受命/死亡/格擋過濾；弓弩原生條件使用 7/12，PO3 腳本武器型別依 round 11 保留 7/9。
- 42 主法術變體（原 22 加風潛行、血四檔、雷五檔與 additive 增量）、11 quiet bonus MGEF/SPEL。主法術嵌入原已交戰效果 30 秒；差額沿用相同學派、抗性、元素關鍵字、Novice casting perk，NoHitEvent、零衝擊/聲音/學派 XP，避免重播主特效。
- `RefreshProcMagnitudes` 只在數值不同時寫共享法術；讀檔使快取失效而重寫全部元素。新 Float[64] cache 在事件註冊前配置，失敗走原 BreakState latch；無 `arr == None`。
- `ESSBNodes.Rank/Br` 讀 Controller mirror；Trees 匯出 rank/branch/level。SyncStage 快取；Guard 用本地 GLOB/NodeBits 早退，GDivineArmed 與 StartDeferredKill 仍有成對解除，九原生防護視窗不改。
- `ESSBInput` 提前發布形態 GLOB，Controller 用最新 GLOB 合併過時切換請求；力量也走 Input。Numpad 1–9、0、decimal 為 11 形態預設鍵；MCM 熱鍵頁可改鍵、停用、關閉通知/聲音。開形態魔力 10% 門檻、免費許可、失效實體/StateBroken/Ready、死亡、選單、文字輸入均有測試。
- 形態全身 aura 不再掛載；33 自有武器 shader/effect（11×dim/mid/bright），無 fade transition。舊光效記錄 ID 保留。武器能力的 AddSpell/RemoveSpell 仍走 Controller，符合 §4.4 的本期限制。
- schema 6→7：MainQuest 006008→00600A，MCMQuest 006009→00600B；006008/006009 變為 Schema6 inert stub，無 VMAD、flags=0、無 aliases。舊版全部 stub 仍保留；lock 由 round-9 preflight 從原 schema6 lock 生成，非手改 signature。SEQ/VMAD 全指新任務。DebugLevel 000811。

### 玩家倍率：變數 → 寫入/變更點 → 已接刷新

| 變數/依賴 | 寫入或事件 | 刷新 |
|---|---|---|
| 全部元素/初始資料 | Setup、讀檔 invalidation | InitProcCache、RefreshSyncStage、RefreshProcMagnitudes；Ready 前完成 |
| RankCacheA/B、BranchCacheA/B、LevelMirror | Trees.RefreshTree、RefreshActive | 匯出後刷新 Sync/Proc；另更新 Guard.NodeBits、Input 免費節點資格 |
| 活躍樹、形態 | RefreshTrees、SwitchForm、OnFormSwitched | RefreshSyncStage/Proc；先寫全元素強度，切換後更新窗口 |
| 同調點/階段/持續滿 60 秒 | AddSync、PushSyncStage、OnSyncStage、TickTimers | 點數變更重算快取；階段事件刷新 Proc；計時跨階後更新 GLOB/Divine/Proc |
| 基礎倍率、節點倍率、學派/削魔滑桿 | RefreshRuntimeValues、RefreshAbilities、RefreshTrees | 全 42 變體刷新；雷削魔 magnitude 獨立 cache |
| MoltenLeft | SetMolten、TickTimers 到期 | 刷新 Proc；原熔身自身資源邏輯保留 |
| OpenBoost[] | SetOpenBoost、TickTimers 到期 | 刷新 Proc |
| EndBoostLeft/Amount | SetEndBoost、TickTimers 到期 | 刷新 Proc |
| BloodthirstLeft | SetBloodthirst、TickTimers 到期 | 刷新 Proc |
| SelfOverheat | AddSelf/ClearSelf kind 4、ClearSelfAll | 刷新 Proc；原封頂/爆發/清除流程原樣 |
| EnvNight | EnvCheck 值變更 | 刷新 Proc；白天聖、夜晚暗加成保留 |
| 玩家血量/潛行/重擊/右手武器 | 原生命中條件每刀評估 | 選已烤好的 blood/wind/power 變體；不新增輪詢 |
| 目標熱度/印記/凍結/詛咒等 | 原 GetStack/host lazy Tick、原 TargetDamageMult | 不進玩家快取；差額讀舊路徑，<=0 不施法 |

### 離線引擎記錄證據與限制

唯讀掃描 `Skyrim.esm`、本機 Ordinator、Phenderix，機讀證據 `build/fix18-engine-evidence.json`。

- EP51 native Select Spell：原版 `TrickShot` 105F1A、`HackAndSlash30` 03FFFA、`Limbsplitter30` 0C5C05；Phenderix `ZZPerk_PoisonParalyze` 29FB10。DATA = [51,10,3]，EPFT=5，EPFD 為 SPEL reference。本機統計原版 57、Ordinator 132、Phenderix 1 段（文件的 129 是其他快照，不拿來硬套本機檔案）。
- 條件分頁/priority：Ordinator `ORD_Arc70_PinningShot_Perk_70` 058F62、劍類 NPC 05F56F 有多個 EP51 段，PRKE priority 非相同且條件互斥。它證明記錄格式，不證明同時命中多條件時 all/first；本輪使用明確遞減 priority。
- `GetEquippedItemType` 函式 597，弩值 12：Ordinator `ORD_Arc20_Wingstrike_Perk_20` 0064D3、`ORD_ArcMAX_PerfectAim_Perk_MAX_OrdASISExclude` 007526。避免把 Papyrus Weapon.GetWeaponType 的 9 當成 CTDA 列舉。
- `HasMagicEffectKeyword` 函式 699：Ordinator `ORD_Hea60_BreakUponMe_Perk_60` 00803A、`ORD_Res70_BastionWard_Perk_70` 014E7C、`ORD_Ill70_ShadowRefuge_Perk_70` 01F70E。浴火/水膜/影甲三處 693→699。
- 需實機：多 EP51 全部套用或首段即停、0x1D 是否放大 EP51 法術、拳腳/致死刀時序、OnSpellCast/瓦希安、GLOB 切換與視覺實際延遲。`build/fix18-probes.md` 列操作、通過條件及 fallback。獨立 opt-in ESP 8 記錄、唯一 master Skyrim.esm；未加進正式插件或自動啟用。第 2/3 期披風/階梯問題本期未碰，不聲稱已解決。

### 驗證資料

- 代表性 outgoing hit：pre-fix18 **165 = 115 scripted + 50 native** → **101 = 70 scripted + 31 native**，少 64 次（約 38.8%）。由相同 `fix12_cost.scenario`／`papyrus_harness.py` 執行真實源碼計數；不是遊戲幀延遲量測。
- 熱度 4：engine 11.55 + bonus 3.696 = old 15.246；熱度 0、未結算但已逾 6 秒、不同 rank 都驗 equality tolerance 1e-4；新舊 GetStack/host Tick 次數與結算結果相同。
- 6 玩家狀態序列共 120 比較；重複 RefreshProc 寫入 0。另 88 目標倍率組合（含開印、連殺、跨元素倍率）、88 血位/血怒/反轉邊界、200 SyncStage 樣本、15 Input gates。Guard idle 對 Controller 零呼叫。
- FormID 差異：3941→4067，新增 126（124 本期記錄＋2 schema6 stub）、刪除 0；僅兩個任務搬移。詳 `build/fix18-formid-diff.json`。
- 完整 build 及最終狀態以 `build/fix18-build-final.log`、`build/fix18-check.json`、`build/fix18-final-preservation.json` 為準；未部署、未執行遊戲。既有 PLAN COVERAGE 的穩步可選 deferred 項保留，unmapped 仍為 0。
