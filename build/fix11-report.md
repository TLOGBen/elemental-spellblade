## Round 11：弓／弩命中入口修正

- 本輪只修正 `ESSBController.OnWeaponHit` 的來源解析與拒絕紀錄；未增加事件入口、成員變數、master、等待迴圈或更新訂閱。`ESSBGuard.psc` 維持逐 byte 不變。
- 根因界線：舊程式在 `akSource as Weapon` 失敗後把型別當成 0，有投射物即退回。離線用相同事件分別傳 `Ammo`、`None` 可重現無 proc、無印記、無反應且無紀錄。這證明丟棄路徑，尚未證明遊戲中 PO3 真正傳入哪種來源。
- `vendor/imports/PO3_Events_Alias.psc` 與 MO2 已安裝 `powerofthree's Papyrus Extender/Source/scripts/PO3_Events_Alias.psc` 完全相同；都只宣告 `Form akSource`。本機發行包沒有 C++ 事件派發原始碼；沒有使用網路。
- 另外讀取同一發行包的 `SKSE/Plugins/po3_PapyrusExtender.pdb`，從 CodeView `LF_ENUMERATE` 讀回 `RE::HitData::Flag`：`kBlocked=1`、`kBlockWithWeapon=2`、`kBash=16384`、`kTimedBash=32768`、`kExplosion=1048576`，合計 `1097731`；`kSneakAttack=2048`、`kPowerAttack=65536` 不在遮罩中。因此保留所有既有拒絕位元。旗標值可證實，實際箭擊是否帶有該遮罩位元仍須遊戲紀錄確認。
- 新增無狀態 `ResolveHitWeaponType`：`Weapon` 採原武器類型；`Ammo`、`None`、與 `akProjectile` 相同的 `Projectile` 僅在有投射物且攻擊者裝備弓／弩時回退。支援右手及左手查詢；其他來源一律 -1。`None` 且無投射物只在雙手裝備類型皆為空手時接受為 0，避免把法術或未知 Form 當成拳腳。
- 弓／弩仍須帶投射物，近戰仍須無投射物；8 法杖、非武器來源、爆炸、盾擊與格擋均拒絕。遠程 `power = sneak`，普通箭擊不因 65536 取得重擊倍率，潛行箭擊走既有 ×1.5 路徑。來源回退後的武器也傳給既有無形態命中路徑。
- 每個入口拒絕分支呼叫 `LogRejectedHit`，包含 not-operational、disabled、blocked-bash-explosion、invalid-actor、unsupported-source-or-weapon、ranged-without-projectile、melee-with-projectile、invalid-element。輸出 `[ESSB][hit-reject][L3] target=... reason=... sourceType=... sourceFormID=... weapon=... projectile=... flags=... rejectedMask=...`；FormID 及 FormType 為 Papyrus 原生整數表示，None 為 0。level <3 先退出，不探查 Form、不組字串；使用既有 `LogThrottled` 的 0.5 秒重複抑制、20 行／秒及 dropped 計數。
- `ESSBGuard.OnHitEx` 沒有同樣的全域武器來源轉型 gate。8 個 Weapon／Ammo／None／Projectile × 弓／弩事件，均執行岩甲、冰盾、水鏡消耗各一次，並不觸發近戰限定反震；保留原設計。
- 驗證直接執行選定 Papyrus 函式內容，原生 API 使用明確 mock：86 個攻擊案例含所有 0–7、9 武器、空手、staff、spell、explosion、bash、blocked、來源回退及潛行倍率；同一近戰主事件加投射物副事件、法術副事件只產生一次 proc／XP／同調。`ApplyProc`、`OnValidHit`、`InstallMark`、`OpenMark` 實際執行到 mock 原生施法及 reaction 呼叫邊界，不冒稱完整 Skyrim 排程／傷害引擎模擬。
- `build/fix8_verify.py` 原本要求整個命中事件逐字不變；本輪改為 gate 後的既有機制仍逐字相同（只排除新增 invalid-element 紀錄），gate 由 `build/fix11_verify.py` 行為案例驗證。`build/papyrus_harness.py` 加入 Weapon／Ammo／Projectile 語法與可選的紀錄執行；FIX11 使用嚴格原生轉型 mock，並真正執行所有拒絕及節流測試。首次完整建置在 FIX9 舊測試替身缺少裝備 API 處停止；修正舊測試的紀錄跳過規則後完整重建成功，未改 FIX9/FIX10 規則。
- `python build_v03.py` exit 0：19 scripts 全部 0 errors / 0 warnings；READBACK masters `['Skyrim.esm']`、records=manifest=3917；CSF 13/13；DELIVERY、LAYOUT、DOT、MCM、SCHEMA、FIX9、FIX10 均 ok；PLAN COVERAGE 542 rows、0 unmapped；新增 `FIX11 RANGED ok: 86 outgoing cases; 8 incoming arrows; proc/mark/reaction; melee duplicate gate; rejected-hit throttle; FormIDs unchanged; schema 3`。
- 與 `.codex/pre-fix11-snapshot/v03-formids.json` 比對 3917 筆完全相同；`ESSB_DebugLevel=0x000811`；`settings.json` 與 `state-schema.lock.json` 未變，`state_schema_version=3`，本輪沒有增加成員變數，因此不升版。FIX10 檢查輸出的「兩個 quest ID changed」是相對其第 10 輪前基線，本輪沒有任何新增變更。
- 原有編碼、CRLF／LF 保留，實作紀錄只追加；規劃檔、review-*.md、fx_extract.py hash 未變。未讀写 `.strategic-advance/**`；沒有寫入 MO2 或 SkyrimSE，沒有部署到執行中的遊戲。
- 交付：`build/Elements-Spellblade-fix11.zip` 與 `package/Elements Spellblade/`；完整建置紀錄 `build/fix11-build.log`，案例與 PDB 證據 `build/fix11-check.json`，修改差異 `build/fix11.patch`，進度 `.codex/impl-fix-round11.html`。
- 驗證界線：未進行遊戲內測試。來源缺失時只能採命中當下的裝備；箭在空中便卸下／換掉弓弩可能被拒絕，會有 level 3 診斷。`None`+projectile 的識別依賴 PO3 的 weapon-hit 事件來源及裝備弓弩，沒有增加 magic/projectile-hit 訂閱。下一次在測試存檔開 level 3，確認 `[ESSB][hit][L2]` 出現 `weapon=7/9` 並有 proc／印記／反應；如仍無反應，交叉檢查 `hit-reject` 的來源類型、FormID 與旗標。level 3 的預期負載不代表正式遊戲手感。
