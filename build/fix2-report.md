

## 2026-09-17 23:20 Asia/Taipei — fix round 2（首次實機回饋）

本輪依 `.codex/smoke1-Papyrus.0.log` 完整事件區塊盤點：僅納入 stack 觸及 ESSB 腳本的 Error，共 **78 次、9 條錯誤路徑**。`Int[]`／`Float[]` 各 15 次，合計 30 次（與任務描述的 12 次不同，以實際 log 為準）；沒有其他 ESSB Error／Warning 類別。其他模組不處理。

以下 FIXED 表示來源碼修復及離線驗證完成；完整編譯與實機結果尚未完成，不能視為整輪驗收通過。

| 狀態 | 項目／錯誤路徑 | 次數／結果 | 原因與修正／未完成原因 |
|---|---|---:|---|
| FIXED | CancelSwap：Cannot cast from None to Int[] | 15 | 未使用的舊陣列被指定 None；移除該指派，保留每目標備份。 |
| FIXED | CancelSwap：Cannot cast from None to Float[] | 15 | 同上；實際狀態仍由 BackupInts／BackupFloats 分槽保存。 |
| FIXED | ESSBStatus.OnEffectFinish → UnregisterForUpdate | 25 | AME native 已解除綁定；先設 Finished，不再在 finish 回呼呼叫 native unregister。 |
| FIXED | ESSBStatus.OnUpdate → RegisterForSingleUpdate | 7 | Tick 期間效果可能結束；入口與 Tick 返回後檢查 Finished／Migrating。 |
| FIXED | ESSBMark.OnEffectFinish → OnMarkFinish → EndMark → FinishMark → Dispel | 7 | 結束回呼再次消除自身；傳遞 akFinishing，略過該 AME 的 self-dispel，保留 End／XP／FX。 |
| FIXED | ESSBStatus.OnEffectStart → RegisterForSingleUpdate | 5 | 控制器回呼期間效果可能結束／換宿；回呼返回後重新檢查旗標。 |
| FIXED | ESSBMark.OnEffectStart → OnMarkStart → Dispel | 2 | 遲到的起始回呼拒收已結束印記；改呼叫 DispelIfActive。 |
| FIXED | ESSBStatus.OnEffectStart → OnStatusStart → PrepareSwap → UnregisterForUpdate | 1 | 拒收已結束宿主仍取消 native 排程；PrepareSwap 僅設 Migrating，殘留單次 tick 直接退出。 |
| FIXED | ESSBStatus.OnEffectStart → OnStatusStart → Dispel | 1 | 拒收已結束宿主仍消除 native；所有 status 消除路徑改用 DispelIfActive。 |
| FIXED | 13 棵 CSF 技能樹、版面斷言 | 13/13 | x=-4.275..4.275、y=0..4、最小間距 0.95；三路並排，同階分支橫排，第三分支保留額外欄。links／節點／perk 僅座標外全數不變。 |
| FIXED | UTF-8／原行尾、設定按鈕標籤保留 | 3 scripts | ESSBMark 保持 LF；ESSBStatus／ESSBController 保持 CRLF；build_v03.py 的短按鈕標籤未改動。 |
| NOT FIXED | 完整 python build_v03.py 驗收、17 支 PEX 重編 | 未執行 | 既有建置需唯讀 Skyrim.esm、MO2 來源插件及執行 MO2 PapyrusCompiler.exe，超出本輪 read scope；campaign root 無編譯器，未越權存取。已請求此必要例外。 |
| NOT FIXED | 修正後實機重測 | 未執行 | 遊戲仍在執行；未安裝至 MO2，未操作遊戲。不能宣稱新 log 已零錯誤。 |

驗證證據：

- `python build/fix2_regression.py`：11/11 通過；實際 Papyrus function bodies 搭配 native mocks，涵蓋控制器／Tick 期間結束與換宿、遲到 callback、主／副印記自然終焉、主動終焉與 8 槽備份保留；並以故意破壞 bounds／spacing／links／階序確認版面斷言會拒絕。不是 Skyrim runtime。
- `python build/fix2_prior_regression.py`：前輪 23/23 情境通過；只將舊假 AME 的 `Dispel` 介面配合改成 `DispelIfActive`，測試條件不變。
- 範圍內獨立執行 `write_csf`：`LAYOUT ok: trees=13/13 x=[-4.5,4.5] y=[0,4.5] min_spacing=0.95 >= 0.9; tier order + route separation + mainline/branch links valid`；CSF 13 個皆通過原有參照與 JSON 檢查。
- 目前 `build/v03-formids.json` 對 `.codex/pre-fix2-snapshot/v03-formids.json`：3878 筆完全相同，`ESSB_DebugLevel=0x000811`。這是完整重建前的比對；重建後仍須通過新增的 snapshot 斷言。
- 沒有新增 master／record，也沒有新增 `Utility.Wait`、持續性 `RegisterForUpdate`、`Spell.Cast` 或敵人 health `DamageActorValue`。
- 全部操作限 campaign root；沒有存取網路、MO2 或 SkyrimSE，未動規劃、review、`fx_extract.py`、`.strategic-advance/**`。三支 src 的 UTF-8 與原行尾以位元組檢查保留。

產物／狀態：`src/ESSBController.psc`、`src/ESSBMark.psc`、`src/ESSBStatus.psc`、`build_v03.py` 已修改，13 份 package CSF JSON 已更新；**package 的 PEX 尚未重編，因此目前不是本輪可安裝成品**。待前述唯讀依賴授權後執行完整建置，補上 READBACK／DELIVERY／PLAN COVERAGE／17 scripts 結果。進度及 13 棵座標預覽在 `.codex/impl-fix-round2.html`；錯誤清單、回歸結果分別見 `build/fix2-log-errors.json`、`build/fix2-regression.json`、`build/fix2-prior-regression.json`。
