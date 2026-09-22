# Round 18 遊戲探針（round18f 第三題與設定強化；新版待遊戲重測）

正式包：`package/Elements Spellblade/`。選配探針：`build/fix18-probe-package/Elements Spellblade Round18 Probes.esp`。本輪未寫入 MO2 或遊戲目錄；正式包逐檔對齊目前 MO2 部署版，更新的探針包仍需手動安裝。

使用可丟棄的新存檔；正式包測試需自行在 MO2 安裝正式包；提前探針請依下節使用獨立測試設定檔，安裝完整選配資料夾。此輪權限不包含寫入遊戲存檔，因此提供離線探針包及操作卡，不虛構已建立存檔。新檔將火樹保持等級 1、除錯等級設 1，再開火形態。可用主控台 `coc Riverwood` 到測試區，選沒有同伴、平民的安全位置。

## 正式包：每項約五分鐘

| 探針 | 操作與判讀 | 不符合時的既定退路 |
|---|---|---|
| 原生命中 | 火形態用近戰武器砍敵人；命中時立即有基礎火傷/衝擊。熱度差額及印記仍可能晚到。 | 檢查玩家是否有 `ESSB_P_HitProc`、`ESSB_Enabled`、`ESSB_FormActive`、`ESSB_CurrentElement`；不要把腳本差額延遲當成基礎路徑已失敗。 |
| 拳腳 | 收武器打一拳，觀察同樣原生附傷。 | 若拳腳不觸發，依計畫在後續以武器型別 0 的 `OnWeaponHit` 腳本補回；本包未假裝已確認引擎支援。 |
| 弓與弩 | 普通射擊及潛行射擊各一次；兩者都有衝擊，後者基礎倍率 1.5。弓、弩分開測。 | 若裝備型別条件不生效，改用武器分頁 `HasKeyword(WeapTypeBow)` 路徑；型別 12 已有 Ordinator 位元組旁證。 |
| 瓦希安 | 啟用 Ordinator 瓦希安時記錄剩餘法術次數，武器命中 10 次再比較。 | 次數下降即回報：計畫沒有可自動採用且保持玩法的退路，需要使用者決定。 |
| 友軍 | 對跟班/召喚物的命中不得附加本模組元素傷害；跟班被敵人命中也不應進玩家受擊流程。 | 核對 entry point 的目標分頁 453/700 與 Guard 對象篩選。 |
| 切換 | Numpad 1 開火，再按 Numpad 2 切冰，下一刀應為冰。按同鍵關閉；MCM 可改鍵、關熱鍵、提示及音效。 | 先檢查 GLOB 是否已先更新。依 §4.4，能力/武器光仍經 Controller，可能晚 0～數秒；這項視覺延遲與下一刀元素分開記錄。 |
| 致死刀 | 火形態殺死殘血敵人，查看 L1 kill 行。 | 記錄 element=1 或明確的 0；死亡先後為原生未知項，不為追認元素而改寫既有死亡結算。 |
| 聖佑安全 | 持有相應節點、滿足武器/形態/同調條件後承受致死傷；確認觸發一次、離開條件解除保命鎖。 | 若不能解除或重複觸發，停用測試存檔並提供 log；離線已跑 StartDeferredKill 與九防護視窗回歸。 |

## 提前探針：三題、四個能力

安裝完整 `build/fix18f-probes-install.zip`，或 `build/fix18-probe-package/` 裡的 ESP、四支 `Scripts/*.pex`、`SEQ/`。以 SKSE 啟動 Skyrim SE 1.5.97；ESP 的唯一 master 仍是 `Skyrim.esm`。使用獨立測試設定檔、可丟棄存檔，正式 Elements Spellblade 關閉。新版更新了量測器與設定腳本，請使用全新的測試存檔，不沿用執行到一半的舊 meter。

已讀取 `.codex/smoke8-probe-results-Papyrus.0.log`：校準 k=0.95；第一題 A=0、B=1，normalized delta 約 7.000412，對應 `exclusive`；第二題 normalized delta=20，`tier_multiplier_mode = entry` 已成立。第一題的這項新 verdict 只是把已觀察到的情況正確命名，不修改正式設定。正式包 `ESSB_P_HitProc` 的 74 個 entry 51 仍由 exactly-one-true truth table 保護；跨其他 perk 的問題由第三題量測。

### 最短操作

1. 收藏四個次級能力：「探針：準備＋第一題」、「探針：第二題」、「探針：第三題」、「探針：清理」。任務在初始化／讀檔時補發。
2. 到空曠平地，施放「準備＋第一題」。自動保存玩家原 AttackDamageMult、卸裝、裝備原版鐵匕首 `0001397E`、攻擊倍率歸零，生成並準備強盜。
3. 每個量測 session 都做兩刀：等 `READY CONTROL` → 普通砍一刀 → 停手，等 `CONTROL physical-only hit = 0`、`CALIBRATE`、`REFERENCE ... accepted`、`READY PROBE` → 再普通砍一刀 → 等 `MEASURE` 和 `VERDICT`。不要依固定秒數提前砍；以 READY 為準。
4. 「第二題」切換為倍率 perk 組；按相同兩刀程序量測。
5. 第一次施放「第三題」是變體 1，再次施放同一能力是變體 2；**兩次施放各重跑控制、校準、正式刀**。日誌 `MODE=3` 代表第三題變體 1，`MODE=4` 代表第三題變體 2。`SETUP PROBE=3 variant2=False/True` 也可辨識。第三次施放回到變體 1；只有成功掛 meter 才輪換。
6. 施放「清理」：關 gate、失效化 session、移除全部七個探針 perk 和 meter、刪除腳本保存的強盜、還原第一次準備前的攻擊倍率，也移除新增「第三題」能力並重設變體。其他三個操作能力與匕首保留，卸下的裝備不會自動重穿；若需再測第三題，讀檔會補發。結束後丟棄測試檔。

第一題每次換新強盜；第二／第三題沿用活目標，若死亡、停用、刪除或參照無效則換新。可直接從第二／第三題開始。Busy 期間重複施放會拒絕，不會覆寫原攻擊倍率。請勿混用人工 `forceav`／`tai`／人工掛 meter：本版能力已管理這些準備工作。

### 目標準備與可命中性

強盜仍為原版 `EncBandit01Melee1HKhajiitM`（`000C3CA0`），放在玩家前方 128 單位。先以 disabled 建立以定位，Enable 後最多輪詢 10 秒等待 `Is3DLoaded()`；只有 3D 成功載入後才設定 AI／限制動作。**保留 AI 啟用，使用 `SetRestrained(True)` 與 `SetDontMove(True)`，並明確 `SetGhost(False)`**，不再於初始載入前 `EnableAI(False)`。這樣保留角色的 AI／動畫處理，限制自主動作與移動，而不採用 ghost 或停用角色的方式固定目標。

3D 載入不等於所有外掛初始化完成，所以再等 2 秒、卸裝清空背包，之後每 0.5 秒檢查一次，最多 30 次。FireResist、MagicResist、AbsorbChance、HealRate、HealRateMult 以 `ModActorValue(wanted - current)` 修正目前殘差；Health 以 `10000 - GetActorValueMax(Health)` 調整最大值後補滿。每次修正都重新讀實值，33→0、外部移除能力造成 -33→0 都能收斂，不重複疊加固定負偏移。

需連續六個半秒區間在區間前後都符合抗性／回血=0、目前及最大生命=10000，才完成 SETTLE；超時、死亡、停用或 3D 消失則失敗。加上題目的 perk 後、掛 meter **緊前**再檢查一次。量測啟動後不再修正 AV，以免掩蓋傷害；原 `ENV`／`Clean()` 抗性與回血零值要求不變，後續外掛仍持續改值就拒絕，不硬算 verdict。

離線已確認本機 Papyrus API 的 native 簽名、四支 PEX 編譯、3D 等待順序、AI 保持啟用、非 ghost、限制移動呼叫，以及延遲 AV 增減／健康值穩定流程。**離線無法執行 Skyrim 的碰撞與命中判定**；實際可命中性仍以新版遊戲中的匕首 `HIT` 與 `CONTROL` 為準。若 `READY CONTROL` 後完全沒有匕首 HIT，保留日誌回報，不宣稱已有碰撞修復實測。

### 探針 1：同一 perk 的 winner

`ESSB_ProbeAB` 的 A entry priority=200、標稱火傷=5；B priority=199、標稱火傷=7，兩個條件同時成立。歸因沿用 segment 1=A、segment 2=B。

| 有效段落與 normalized delta | verdict／設定值 |
|---|---|
| A=1、B=1、C=0，12 | `both segments fired (5+7): lightning_roll_mode = additive` |
| A=1、B=0、C=0，5 | `only the first segment fired (5): lightning_roll_mode = chain` |
| A=0、B=1、C=0，7 | `single winner = last processed / lowest priority (7): lightning_roll_mode = exclusive` |
| 其他數值、重複／缺少段落或污染 | `unexpected, report` |

第三列是 smoke8 已觀察到的結果；不再誤報 unexpected。數值容差仍為 normalized delta ±0.15。

### 探針 2：0x1D entry point 法術倍率

只有 `ESSB_ProbeMagnitudeHit` 與 `ESSB_ProbeMultiply`。C=1、A=B=0：normalized delta=20 → `tier_multiplier_mode = entry`；10 → `spell_variant`；其他／污染 → unexpected。smoke8 已證實 20；新版仍保留回歸測試能力。

### 探針 3：跨 perk 共存（兩個變體）

每組兩個 **分開的 PERK**，各只有一筆 entry 51。兩者與第一題相同 gate／meter target／目標條件，在同一刀同時為真；使用原 A/B 法術及原歸因。兩個 perk 都只有一個 rank，entry rank 都是 0，排除 rank 差異。A 永遠先 AddPerk、FormID 較低；B 後 AddPerk、FormID 較高。

| 變體／MODE | A：5 傷、segment 1 | B：7 傷、segment 2 |
|---|---|---|
| 1／3 | `xx000850` CrossA，priority 200 | `xx000851` CrossB，priority 199 |
| 2／4 | `xx000852` CrossA2，priority 199 | `xx000853` CrossB2，priority 200 |

`xx` 為探針 ESP 實際載入序，只供解讀，不用手輸指令。兩個變體互斥；任何半組、混組、混入第一／二題 perk 都被拒絕。

| 一次測試的有效結果 | VERDICT |
|---|---|
| A=1、B=1、C=0，normalized=12 | `cross-perk additive: coexistence OK (12)`；`cross_perk_mode = additive` |
| A=1、B=0、C=0，normalized=5 | `cross-perk single winner A (5)`；列較低 FormID、當次 priority、先加入、相同 rank；`exclusive` |
| A=0、B=1、C=0，normalized=7 | `cross-perk single winner B (7)`；列較高 FormID、當次 priority、後加入、相同 rank；`exclusive` |
| 其他傷害、段落數、無效環境 | `unexpected, report`，不推斷共存 |

把兩次有效結果並排解讀：

| 變體 1 → 變體 2 | 資料允許的推論 |
|---|---|
| 12 → 12 | 受測配對支援跨 perk additive，共存路徑通過此探針。仍須實測 Ordinator 的具體同時觸發技能；這不是對所有 129 個 entry 的全量相容保證。 |
| B(7) → A(5) | 跟隨最低 entry priority=199；支持 priority 決定單一 winner。 |
| A(5) → B(7) | 跟隨最高 entry priority=200；支持 priority 決定單一 winner。 |
| A(5) → A(5) | 跟隨 A／較低 FormID／先加入，而非固定高低 priority；兩次仍無法拆開 FormID、加入順序或特定法術身分。 |
| B(7) → B(7) | 跟隨 B／較高 FormID／後加入；同樣不能分辨這幾項。 |
| additive 與單一結果混合，或 unexpected | 保留兩組完整 log，不決定一個全域共存模式。 |

單次 winner 的 log 只列相關屬性，**不聲稱已證明遍歷規則或 FormID 決定原因**。相同 rank 已控制住，其他模組能力仍可能混淆；若要拆開剩餘因素需另做更多受控試驗。正式包不因本探針結果自動改寫。

### 控制刀的額外 OnHit 例外

仍保留每個 OnHit，累計 `hits`、`weapon_hits`、`extra_candidates` 與完整 `sources`。只有以下條件全部成立才忽略額外事件：未校準、不是 REFERENCE、正處於物理控制刀；恰好一個 TestWeapon 命中；其餘非空來源的 Form type 不是 WEAP(41)、SPEL(22)、PROJ(50)；aggressor 都是玩家，無 projectile／重擊／潛行／盾擊／格擋／穩定性等待期的命中；傷害差 **精確=0**、A/B/C 都為 0，其他環境與穩定性檢查也通過。

日誌會寫 `IGNORED control extra events=...`，附總數、來源及「一個測試武器事件、非武器／法術／投射物、穩定物理差精確為零」理由。像 `63000E76`、`FE38982D` 這類事件以當下 `GetType()` 判斷，不以硬編碼載入序白名單放行；缺少匕首、兩次匕首、+/-0.001 生命差、任何探針段落都不放行。為保守起見連外部法術事件也拒絕。

**REFERENCE 與正式 PROBE 刀完全不套用此例外。** 這兩段出現額外 OnHit 仍拒絕；不以「剛好接近 5／7／12／20」來放行，以免改變 verdict。遇到持續污染時，依拒絕來源定位造成額外事件的效果後重試，不將 invalid 當作共存失敗。

### 日誌、校準與邊界

搜尋 Papyrus.0.log 的 `[ESSB-PROBE]` 行。每次保留完整 `SETUP`、`SETTLE`、`MODE`、`ENV`、`HIT`、`SEGMENT`、`MEASURE`、`VERDICT`。`SETUP fresh_meter=True` 只代表加上 ability，不代表量測器已接受環境；以 READY 為準。

- CONTROL：gate 關閉，物理生命差=0。REFERENCE：自動由同一玩家對同一目標施加無探針 keyword 的原生 10 點火傷，segment 4 一次、無 OnHit，兩次生命讀數穩定。
- `k=reference_delta/10`，只接受 [0.2,2.0]。所有正式 verdict 依 `health_delta/k`，±0.15；reported magnitude 只供診斷。k=0.95 時 4.75／6.65／11.4 的實際生命差分別對應 5／7／12。
- 零火抗、零魔抗、零吸收、零回血與零玩家攻擊倍率保持強制。不要塗毒、附魔、徒手、換武器、開無敵／幽靈、連砍或讓其他角色攻擊。每次最後事件後等待 3 秒，再以間隔 1 秒的兩個生命讀值驗證穩定。
- 舊 session／其他目標事件被忽略並記錄；穩定期新命中／段落、生命漂移、死亡、低生命、漏事件、非法段落與 perk 變更都拒絕。STOP 後修正來源，重施放能力重跑控制與校準。
- k 不能消除只針對特定法術／keyword／entry-point 路徑的倍率、傷害上限或期間變動；因此跨 perk 成功只代表此實驗條件下成功。

### 離線驗收與可重現建置

`python -B build/fix18f_rebuild.py` 會以 scope bootstrap 執行完整 **`python build_v03.py`**。所有原有建置及檢查都執行，產生的非探針 source 寫到 `build/round18f/rebuild-N/`，不越過本輪允許的 src 寫入範圍；無網路、無 MO2／SkyrimSE 寫入。

保留全量原始重建 PEX。由於 PapyrusCompiler 的時間戳／宣告順序不具決定性，正式包重新編譯後先比對解碼後的指令、屬性、除錯資料、字串等，再使用已證明等價的原 PEX 組裝；36 個其他正式檔需原始 bytes 相同。最後 56 個正式檔的 SHA-256 與修改前、MO2 部署版全等，不能用「語意相同」代替正式成品的 byte-identical 要求。

新檢查執行實際 PSC 函式／事件：第一題 7 的 verdict；第三題兩變體的所有正常／異常結果及容差；128 種 perk 子集合；控制刀三種事件順序；參考／正式刀污染等 17 種拒絕；延後 AV 加入／撤回、無 3D、死亡、永不穩定、final check。既有校準、拒絕訊息、20 個抗性守門、設定能力、PEX 與 ESP 回讀也保留。第三題的 4 個 PERK、第四個能力的 VMAD、QUST、SEQ 與唯一 master 都有驗證。

本輪新增內容已完成離線編譯與 harness；**未執行 Skyrim，新版 hittability 與跨 perk 引擎結果仍待遊戲回報**。報告不把 native mock 當作 runtime 證據。
