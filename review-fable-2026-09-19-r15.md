# 審查：fix round 15 是否真的修好 10 項，以及有沒有弄壞別的

- 審查時間：2026-09-19 09:17（Asia/Taipei）
- 比對對象（唯讀）：`.codex\pre-fix15-snapshot\src\*.psc` → `.codex\post-fix15-snapshot\src\*.psc`；另讀 `post-fix15-snapshot\build_v03.py`（只查 MGEF 旗標）
- 上一輪清單：`review-fable-2026-09-19.md`；實作方的說法：`實作紀錄.md` 的「fix round 15」與「08:48 指揮官」兩段（視為主張，不視為證據）
- 實機樣貌（引自上一輪的 `smoke4-Papyrus.0.log` 量測）：事件晚 0–7 秒、控制器 tick 11–34 秒、宿主 tick 約 8 秒、`CloseForm`→`OnFormClosed` 13–23 秒、絕大多數擊殺是一刀物理致死、玩家主用黑暗與水
- 沒有建置、沒有進遊戲。凡是要靠引擎行為定案的都標 medium／low。

---

## 1. 十項判定

| # | 上一輪發現 | 判定 | 依據（post 快照） |
|---|---|---|---|
| 1.1 | 死咒／饕餮／處刑／亡魂從未結算 | **fixed（在引擎允許的範圍內）** | `ESSBStatus.psc:1044-1064` `ResolveDeathCurse`：活目標依真實期限結算（`ESSBStatus.psc:987-989`，且任何一次 `GetStack`／`AddStack` 都會先跑 `Tick()`，所以下一刀就結算，不用等 8 秒宿主 tick）；死亡時由 `ESSBController.psc:5730-5764` `CaptureDeath` → `7181-7193` `SettleDeadCurse` 結算固定項並呼叫 `AfterDeathCurse`（饕餮給玩家）。`CaptureDeath` 現在由致命那一刀的 `OnWeaponHit`（`1634-1637`）事件驅動觸發，不必等 tick。殘留限制見 2.1（Z 融斷落在屍體上時死咒會卡住不結算，是新問題）。 |
| 1.2 | 致命潛行：風附傷×3、風勢直接滿、奇襲、連殺 | **partly** | 風勢直接滿與奇襲：`ESSBController.psc:1622-1633`（旗標在 `IsDead` 早退**之前**寫入；死者走 `SetSelf(3, WindThreshold)`＋`ESSBElem2.LethalAmbush`）— fixed。連殺：`SettleSneakKill`（`7195-7207`）用每目標的 `HitSneak` 而非全域旗標 — 接線正確；但 `ESSBElem2.TryKillStreak`（`ESSBElem2.psc:1115-1140`）仍要求 `aiKillingElement == 5`，而 round 14 的歸屬規則對「純物理一刀、無先前元素傷害、無實印」回 0（`KillElementFor` `5709-5728`）。潛行一刀是風形態最常見的擊殺，所以**連殺在實戰仍不會觸發**；實作方在取捨 3 明說這是刻意的。風附傷×3 對屍體本來就無法施放（正確不做）。 |
| 1.3 | 反擊永遠不加成 | **fixed** | `ESSBController.psc:1808-1815`：`OnNoFormHit` 入口讀 `RiposteLeft` 期限 → `riposte = 1.3` → `ApplyNoFormBaseline(…, riposte)`（`1844-1845`）與 `ESSBNoForm.OnMartialHit(…, afRiposte)`（`ESSBNoForm.psc:48-49`）都乘上；用完歸零。`SwitchForm` 仍清 `RiposteLeft`（`1305`），與「無形態分支」語意一致。 |
| 1.4 | 神佑觸發條件不可能成立 | **fixed（但新增引擎層風險，見 2.2）** | `ESSBController.psc:7277-7301` `RefreshDivineProtection`：資格成立就事前 `StartDeferredKill()`；受擊事件或 tick 看到 `Health <= 0` 才 `SetGuardDivine(2)`＋`ApplyCleanse`＋`RestoreActorValue` 回到 1 血再 `EndDeferredKill()`。不再依賴「傷害後還活著且 ≤1」。 |
| 1.5 | 切換路線的雷終焉永遠 0 電荷 | **fixed** | `ESSBController.psc:1410-1413` `OnFormSwitched` 在 `ClearSelfAll()` 前存 `SwitchCharge`；`ESSBReactions.psc:149-157` reason 0 時 `snapshot = TakeSwitchCharge()`；`OverloadMult(…, snapshot)`（`ESSBElem.psc:708-716`）、`EndShock(…, snapshot)`（`ESSBReactions.psc:181`）、`EndShockNodes(…, aiCharge)`→`SetPendingDischarge(aiCharge)`（`ESSBElem.psc:679-683`）、`AfterOpen` 用存下的值放電（`ESSBController.psc:2233-2236`）。`SwitchForm` 傳的是 `CurrentElement` 值，3 = 雷，對得上。 |
| 1.6 | 兩套時鐘 | **partly** | 控制器所有秒計時器、`OpenBoost`／`EndBoost`、領域、化身、雷雨充電、宿主的浮空／死咒／催毒／星鎖／擴散都改成期限（diff 全數核對）；血毒星痕桶改 `RingClock` 有界補結算（`ESSBStatus.psc:833-875`，horizon = 12）；「先結算再過期」由 `GetStack`／`AddStack` 前置 `Tick()` 做到。**沒修的**：(a) 由 PERK 讀鏡射全域變數的受傷視窗（殘影／神佑／披風／影身／預知／星光／順轉／安全閥／冰盾窗）— `SetGlobal(GGuardDivine, SecondsLeft(…))` 只在設定時與下一次 tick 寫（`3845-3999`），PERK 端看到的 2 秒視窗仍然持續到下一次 tick（11–34 秒）；(b) 融斷 13–23 秒的延遲是 VM 排程，本輪無法也沒有處理；(c) 領域晚 tick 的整批傷害有新問題，見 2.4。 |
| 1.7 | 擊殺層數：詛咒無快照、宿主死亡即消失 | **fixed** | `CaptureDeath` 補 curse／heat／holy（`5741-5743`）；`ESSBElem3.OnKill` 改用傳入 `aiCurse`（`ESSBElem3.psc:1164, 1186`）；`OnStatusFinish` 解除登記前先 `CaptureDeath`（`2523-2525`）；`OnMarkFinish` 對死者只捕獲不跑終焉（`2426-2434`）。`build_v03.py:1495`（11 個 MarkEffect）與 `:1556`（StatusHost）的 DATA 旗標含 `0x00200000`（No Death Dispel）— 只核對建置腳本，未讀 ESP。 |
| 1.8 | 熔斷死程式碼 | **fixed** | `ESSBReactions.psc:239-241` `EndFire(…, aiReason)` → `Detonate(…, !(aiReason == 1 && KeepHeatOnBurst))`；`End` 傳入 `aiReason`（`176`）。 |
| 1.9 | 火葬／亡魂用套用後即時 HP 判殺 | **partly（fixed but loose）** | 改為 `ArmKillProc`（爆燃 `ESSBElem.psc:430`、死咒 `ESSBStatus.psc:1057`）＋ `OnKillEvent` → `SettleKillProc`（`7255-7275`）。兩個方向都偏：(i) 視窗 3 秒內**任何**擊殺都兌現（爆燃沒殺死、2 秒後一刀砍死也放火葬）— 實作方取捨 6 已承認；(ii) `CaptureDeath` 的 `KillProcUntil >= deathAt` 用的是「捕獲時間」不是死亡時間（`5754-5760`），捕獲晚於 3 秒（tick 路徑必然晚）就不標 -1，`OnKillEvent` 也晚於 3 秒時 `due >= now` 為假 → 不兌現。事件晚 0–7 秒的環境下這接近擲硬幣。最小修法見 2.6。 |
| 1.10 | 斷咒判定過晚 | **partly** | `OnNoFormHit` 入口先取 `hitCasting`（`1810`）— 仍是「事件處理當下」，只是提早到傷害前；`RecentCast`（1.5 秒）只對已 `StartCounter` 註冊的目標有效，而註冊條件是**已購反咒** `Br(11,1,1,2)` 且目標**已帶破魔印**（`2729-2737`、`2725-2727`、`ESSBCounter.psc:14-24`）。也就是第一擊、或沒買反咒的玩家，斷咒的判定和以前一樣晚。順帶新增每次無形態命中的固定成本，見 2.5。 |

---

## 2. 新缺陷（依影響排序）

### 2.1 Z 融斷現在會結算屍體上的印記：XP、反哺魔力、水導引同調可從屍體刷，且屍體上的死咒永遠不結算 — 影響 high，信心 medium-high

**觸發**：黑暗（或任何）形態砍死目標（一刀死，這位玩家的常態）→ 按 Z → `CloseForm`→`OnFormClosed` 13–23 秒後才跑。

**為什麼現在會**：round 15 給 11 個 MarkEffect 加了 No Death Dispel，所以印記 AME 在目標死後不再被引擎移除、`OnMarkFinish` 不再在死亡時清格；屍體的登記格要等控制器 tick（11–34 秒）的 `IsDead` 掃描才 `ClearSlot`。在這個視窗內 `OnFormClosed`（`ESSBController.psc:1441-1470`）的迴圈只檢查 `target && (RegElem >= 1 || RegElem2 >= 1)` 與距離，**沒有 `IsDead()`**，對屍體照跑 `ESSBNoForm.OnBurstTarget`＋`EndBothMarks(index, k)`，`burst += 1`。`FinishMark`（`2314-2378`）與 `ESSBReactions.End`（`138-221`）也都沒有死亡守衛，於是屍體會拿到：`Trees.OnEndXP`（`2368`）、`ESSBNodes.OnEndReward` 反哺魔力（`ESSBReactions.psc:213`）、`EndWater` 的 `AddSync`（`357`）、`PlaceFx`，`burst` 計數再餵給 `ESSBNoForm.OnBurst` 的「回流」每印記魔力（`ESSBNoForm.psc` `aiMarks`）。round 15 之前印記死亡即被 dispel，`OnMarkFinish` 以 reason 2 結算一次就清掉，Z 融斷碰不到屍體；現在改成 Z 融斷（含 K_sync 倍率）碰得到。

**連帶**：`EndDark` 對屍體走 `akStatus.SetDeathCurse(3, …)`（`ESSBReactions.psc:366-367`，宿主因 No Death Dispel 仍綁著），但屍體宿主的 `OnUpdate` 已停（`ESSBStatus.psc:805-810`）、`GetStack` 對死者跳過 `Tick()`、`CaptureDeath` 對已捕獲過的目標在 `SettleDeadCurse` 之前就 `Return`（`5732-5738`）→ 這顆死咒永遠不結算，饕餮也拿不到。`ApplyUtil(20, 100, seconds, 屍體)` 也是白施放。

**最小修法**：`OnFormClosed` 迴圈裡對 `target.IsDead()` 的格子改為 `CaptureDeath(index)`＋`ClearSlot(index)`、不計入 `burst`；`FinishMark` 開頭若 `target.IsDead()` 則 `CaptureDeath(aiSlot)` 後只做 detach／dispel、不呼叫 `ESSBReactions.End` 與 `OnEndXP`。（`InstallMark` 的切換終焉走 `OnValidHitInternal`，只對活目標，不受影響。）

### 2.2 神佑：無法排除的引擎層卡死路徑，以及可見的「0 血不死」視窗 — 影響 critical（若發生）／信心 low-medium（取決於未驗證的引擎行為）

我逐一走過指揮官問的路徑，腳本層面的配對是完整的：

- mod 停用（`Enabled = 0`）：`Tick` 不看 `Enabled`（`IsOperational` = `IsCurrentController && !StateBroken && Ready`，`6337-6339`），`3764` 每次 tick 都跑 `RefreshDivineProtection`，`eligible` 含 `Enabled == 1`（`7293`）→ 最遲下一次 tick 解除。`ESSBGuard.OnHitEx` 在 `Enabled != 1` 時於 `RefreshDivineProtection` 之前就 `Return`（`ESSBGuard.psc:78-80, 89`），所以停用後、tick 前的致命傷只能等 tick 的第一分支救回 — 不卡死，但會「以停用狀態被神佑救一次」。
- 關形態：`CloseForm`→`RefreshAbilities`（`1375, 1384`）→ `3027` → 不合資格解除。
- `StateBroken`：`BreakState` 開頭無條件解除（`6342-6345`）。
- schema 升版／舊世代實體：新 `Setup` 無條件 `EndDeferredKill()`（`1184-1185`），`OnPlayerLoadGame` 把 `Ready = False` 並排程 `OnUpdate`→`Setup`（`468-478, 484-487`），所以每次讀檔都會跑到。
- 存檔／讀檔：不論引擎是否把 deferred-kill 存進存檔，`Setup` 先解除再由 `RefreshAbilities` 依資格重上鎖，兩種情況都收斂。

**仍然構得成的卡死**：(a) 玩家在武裝狀態下存檔後**移除本模組**（或 ESP 失效使 `ESSB_MainQuest` 不再存在）— 若引擎把該狀態存進 actor 變更記錄，沒有任何腳本會再呼叫 `EndDeferredKill`，玩家永久不死。這是 `StartDeferredKill` 這個設計本身的代價，不是接線錯誤，但應寫進實作紀錄的已知風險，並建議 MCM 提供「解除神佑保護」按鈕（呼叫 `EndDeferredKill` 一次）。(b) 舊世代 `ESSBTrees`（`ESSBTrees.psc:905-907, 988-990, 1042-1044`）呼叫 `Controller.RefreshAbilities()` 時沒有 `IsOperational` 守衛，而 `RefreshDivineProtection` 自己也沒有 `IsCurrentController()` 守衛：舊實體若還能被叫到，會用自己的 `DivineArmed` 再 `StartDeferredKill`，新實體不知道，之後由誰 `End` 就看引擎把它當旗標還是計數。最小修法：`RefreshDivineProtection` 開頭加 `If !IsCurrentController() Return`。

**可見的行為偏差（不是卡死）**：致命傷發生到腳本看到之間，玩家以 ≤0 血活著、繼續被打、血量負很多。受擊事件晚 0–7 秒；若致命來源不產生 `OnHitEx`（墜落、溺水、法術 DoT、`DamageActorValue`），要等控制器 tick（形態開啟時 1 秒排程但實測 11–34 秒）。之後 `RestoreActorValue("Health", 1.0 - HP)` 回到剛好 1 血，再靠 `GGuardDivine`（見 1.6(a)）擋到下一次 tick。設計寫「致命傷改為留 1 血」，實作變成「先不死、幾秒到幾十秒後補到 1 血」；請實機確認玩家 0 血時的 HUD／音效／倒地表現是否可接受。

### 2.3 待綁定的冰封（pending 路徑）視窗變成兩倍長，並可能誤觸發換宿的時鐘重置 — 影響 medium，信心 high（純邏輯）

`ESSBController.psc:6022-6034` `SetFrozen`：宿主未綁定時存 `PendingFrozen[slot] = now + DurationSeconds(afSeconds)`（一個期限）。綁定時 `FlushPendingState` 呼叫 `akStatus.SetFrozen(0.0, frozen)`（`6147-6149`）→ `ESSBStatus.psc:460-468`：`FreezeSeconds = Ctl.DurationSeconds(0.0)` = **0**（`2801-2804` 對 ≤0 回 0），`FreezeTime = afDeadline - 0 = 期限本身`。之後 `Tick` 的過期判斷（`888-895`）：`FreezeSeconds > 0.0` 為假 → `frozenSeconds` 退回預設 `3.0 + FrozenExtraSeconds`，條件 `now - FreezeTime >= frozenSeconds` 等於 `now >= 期限 + 3`。結果冰封從請求算起約 6 秒而不是 3 秒。這條路徑在「開印第一擊就湊滿 5 層」或事件晚到宿主尚未綁定時會走到，不算罕見。

副作用：`FreezeTime` 在未來，`RebaseImportedClock`（`ESSBStatus.psc:1039`）在換宿匯入時會把它當成「跨程序」而 `ResetLoadClock` → 所有狀態時戳歸 now、死咒／浮空／催毒期限縮成 now+1。

**最小修法**：`SetFrozen` 在 `afDeadline > 0.0` 分支裡令 `FreezeSeconds = afDeadline - Utility.GetCurrentRealTime()`（若 ≤0 則取 0.01），`FreezeTime = now`；或在 `FlushPendingState` 改傳 `SetFrozen(frozen - now)`。

### 2.4 領域的晚 tick 整批結算打到「剛進來」的人 — 影響 medium，信心 high

`ESSBController.psc:4570-4590`：每個領域格算一次 `ticks = (stop - DomainTickAt) as Int`（可到 34），然後對**當下**在範圍內的每個 victim 施加 `ticks` 倍：死域 `ApplyDotDamage(10, ReactDamage × 0.5 × ticks)`（`4619-4621`）、毒霧 `AddStackTo(victim, 7, ticks)`（`4612`）。一個 1 秒前才走進死域的敵人吃 34 秒份的暗傷（B_max × 17），毒霧一次塞 12 層。實作方取捨 4 說「使用結算時的幾何位置」，但沒說傷害也整批補給新進者。玩家自己的回復（`4578-4588`）同理反向有利。

**最小修法**：`ticks` 上限設成一個小常數（例如 3），或改為每 victim 記首次見到的時間（8 格 `Actor[]`＋`Float[]`，不擴 128）。

### 2.5 每次命中的可避免成本 — 影響 medium（無形態）／low（形態），信心 high

1. `OnNoFormHit`（`1810`）對**每一次**無形態命中無條件呼叫 `ESSBNoForm.IsCasting`：最多 4×`GetEquippedSpell`＋4×`PO3_SKSEFunctions.IsCasting`＋`GetEquippedShout`＋1 次 `IsCasting`（`ESSBNoForm.psc:239-254`），最壞 10 個原生呼叫。round 15 前這段在 `OnManaBreak` 內被 `Rank(11,1,0) > 0` 與 `Br(11,1,1,0)`（斷咒）擋住。修法：`Bool hitCasting = ESSBNodes.Br(Self, 11, 1, 1, 0) && (…)`。
2. `ESSBStatus.GetStack`／`AddStack`／`SetStack`／`AddAstral`（`273-277, 358-362, 394-398, 477-481`）每次都先做 `Holder.IsDead()` 原生呼叫，再進 `Tick()` 才算 `elapsed < 1` 早退（`833-836`）。命中路徑上 `GetStack` 呼叫點共 41 處（控制器 13、Elem 10、Elem2 8、Elem3 8、Reactions 2），一次形態命中通常走 5–10 次，每次多一個原生呼叫。修法：把 `(now - RingClock) as Int >= 1` 的純腳本比較放在 `IsDead()` 之前。另外，宿主 tick 實測 8 秒一次，所以幾乎每一刀的第一個 `GetStack` 都會在命中處理內同步跑完整的 DoT 結算（`ApplyDotDamage`→`DoCombatSpellApply`、`SpreadPoison`、`OnLanding`）— 工作總量沒變，但延遲都堆進命中路徑。這點是設計取捨，列出供判斷。
3. `AddSync`（`3267-3269`）在 `CachedSync >= CachedT3 && !DivineArmed && !DivineSaveUsed` 時每次命中呼叫 `RefreshDivineProtection`（`ThePlayer`、`GetActorValue`、2×`GetValueInt`、`SyncStage`、`Br`）；沒買神佑的玩家在三段時每刀白付 6 次。本場最高 sync=13 未觸及。修法：條件加 `ESSBNodes.Br(Self, 6, 0, 4, 0)`。
4. 227 筆屍體命中（本場 85% 的命中）現在多走 `IsPlayerTeammate`／`IsCommandedActor`／武器型別檢查／`FindSlot`／`SettledDead` 掃描才被拒（`1591-1660`），約 3 個原生呼叫；`CaptureDeath` 有去重，每具屍體只付一次。可接受，列此備查。

### 2.6 火葬／亡魂的 3 秒視窗：既會誤兌現也會漏兌現 — 影響 medium，信心 high（邏輯）

見 1.9。誤兌現：`ArmKillProc` 在每次 `Detonate`／活體死咒都武裝（`ESSBElem.psc:430`、`ESSBStatus.psc:1057`），之後 3 秒內的任何擊殺（本場幾乎都是武器一刀）都放火葬／亡魂。漏兌現：`CaptureDeath` 用捕獲時間比對（`5754-5760`），tick 路徑捕獲必晚於 3 秒。

**最小修法**：`ArmKillProc` 時記下 `beforeHealth = akTarget.GetActorValue("Health")`（`ApplyTrackedDamage` 已用同一招，`5618`），若 `afAmount >= beforeHealth` 就把 `KillProcUntil` 直接設為 -1（預期致死，不受視窗限制）；否則維持 3 秒視窗但在 `OnKillEvent` 也接受 `DeadActor` 環裡的捕獲。

### 2.7 連殺在「先非潛行命中、再潛行一刀致死、擊殺事件先到」時丟失 — 影響 low，信心 medium

`OnKillEvent` → `SettleSneakKill`（`7195-7207`）讀到的是**上一刀**（非潛行）的 `HitSneak`，並把 `HitKillDone` 設 True；致命那刀的 `OnWeaponHit` 隨後到達，死者路徑掃 `SettledDead` 再呼叫 `SettleSneakKill`，但 `!HitKillDone` 已為假 → 不給連殺。另 `SettledElement[settlement]` 在 `SettledDead` 寫入之後、幾個 `GetStack`（跨腳本）之後才寫（`5787-5809, 5811`），這段空窗武器回呼讀到 0。兩者都只在潛行攻擊不是首擊時發生；配合 1.2 的元素歸屬限制，實戰意義不大。

### 2.8 其他小項（列出，不另排序）

- `SetMolten` 重覆呼叫時 `MoltenTickAt = now`（`4167`）丟掉尚未結算的秒數；影響僅耐力回復。
- `KillProcActor` 每目標一格（`7240-7252`），同一目標先爆燃再死咒只留最後一種；可接受。
- `OnKillEvent` 內 `SettledDead` 與 `DeadActor` 各 8 格，`CaptureDeath` 去重後每具屍體一筆，環容量足夠。

---

## 3. 查過、認為乾淨的部分

- **雙重結算**：`ResolveDeathCurse` 在任何會讓出鎖的呼叫之前就把 `DeathCurseLeft = 0`（`ESSBStatus.psc:1045-1051`）；`SettleDeadCurse` 的 pending 分支也先歸零（`7185-7187`）；`CaptureDeath` 以 `DeadActor`／`SettledDead` 去重（`5732-5738`）；`OnKillEvent` 以 `SettledDead` 去重（`5777-5782`）；`SettleKillProc` 取出即清 `KillProcActor`（`7262`）。宿主 `Tick` 的 `Settling` 旗標在 `Settling = True` 到 `Settling = False`（`837-996`）之間沒有任何 `Return`，Papyrus 對 None 呼叫只記錄不中斷，所以不會卡在 True；`ResetLoadClock` 也會清它。
- **讀檔重定基**：控制器 `ResetLoadClock`（`6883-7030`）把全部秒計時器、`OpenBoost`／`EndBoost`、`DomainLeft`、`StormCharge`、`SwitchCharge`、`ChargeDecayAt` 歸零或設 now，pending 期限改 now+1，`HitActor`／`CastActor`／`KillProcActor` 清空；宿主 `ResetLoadClock`（`ESSBStatus.psc:999-1030`）把 `RingClock`／`SpreadCounter` 設 now、四個期限改 now+1。uptime 往前或往後兩個方向都收斂，不會出現「永不過期」。`Setup` 在 `wasLoaded` 時呼叫（`1235-1237`）。
- **換宿匯出／匯入**：`ExportFloats` 24 格（`ESSBStatus.psc:674-704`）帶 6 個新期限；`ImportState` 先讀舊 Int 位置（現為 0）再以 `afFloats[17..22]` 覆蓋（`768-775`），順序正確；`BackupFloatsA/B` 96 = 4×24（`557-570`），`ReadSwapFloats` 24（`6283-6290`）；`RegPendStarLock` 以期限存放、綁定時 `SetStarLock(0, starLock)`（`2495-2501`、`ESSBStatus.psc:577-585`）正確。
- **陣列大小**：新增的 14 個陣列全為 8 格，`OpenBoost`／`EndBoost` 12，`BackupFloats` 96，無超過 128。
- **`== None`**：post 全部 6 處都是 Form／Projectile／Spell／Perk，無陣列（`1554, 1602`；`ESSBGuard.psc:87, 106`；`ESSBPlayerAlias.psc:34`；`ESSBTrees.psc:497`）。
- **電荷衰減**：`3726-3738` 以 `ChargeDecayAt` 補算已流逝秒數，重新命中後 `SelfLastHit` 更新使舊 `ChargeDecayAt` 失效，不會倒扣。
- **雷雨充電、化身**：期限式，晚 tick 只補一次，不會連發。
- **`TakeKillStreak`** 加 `KeepSneakLeft` 期限檢查（`5011-5013`）；`KeepSneak` 期限化（`5000-5002`）。
- **`SetDeathCurseOn` 對死者**（`6062-6065`）直接 `AfterDeathCurse`，與 `SettleDeadCurse` 不會重覆（pending 只在活目標時寫入）。
- **`ESSBStatus.OnEffectFinish` 先 `Tick()` 再解綁**（`104-113`）只對活宿主；`OnStatusFinish` 對死者 `CaptureDeath`（`2523-2525`）發生在 `RegStatus = None` 之前，快照讀得到層數。
- **`RefreshDivineProtection` 的重入**：受擊執行緒與 tick 執行緒同時看到 `Health <= 0` 時都會回血並 `EndDeferredKill`，第二次是 no-op；`DivineSaveUsed` 保證不再上鎖。
- **`OpenBoost`／`EndBoost` 的 `SecondsLeft` 回傳**與所有 `> 0` 呼叫端相容。
- **餘電**：`PendingDischarge` 存實際電荷、`AfterOpen` 取出後歸零（`2233-2236`），`SetPendingDischarge(aiCharge)` 對 0 不會設定。

---

## 4. 不進遊戲無法確認的事

1. `Actor.StartDeferredKill`／`EndDeferredKill` 在 1.5.97 是旗標還是計數、是否寫入存檔、以及與其他死亡替代模組是否共用；2.2 的兩條殘留路徑都取決於此。`vendor/imports/Actor.psc` 不在快照內。
2. 玩家在 deferred-kill 且 `Health <= 0` 期間的引擎表現（HUD、死亡音效、倒地動畫、是否會進 kill-move），以及 `RestoreActorValue` 在該狀態下是否照常生效。
3. ESP 內 12 個 MGEF 的 `0x00200000` 是否真的寫入（只讀了 `build_v03.py:1495, 1556`）；若旗標沒生效，2.1 不會發生，但 1.7 退回未修。
4. `PO3_SKSEFunctions.IsCasting` 與 `MRh/MLh_SpellFire_Event` 在本場負載下相對命中事件的先後；1.10 的判定仍取決於此。
5. `GetStack` 前置 `Tick()` 把 DoT 結算搬進命中路徑後，實際的每刀處理時間變化；實作方報的「116 scripted + 50 native = 166 calls」代表命中若不含 `elapsed >= 1` 的路徑，就量不到 2.5-2 的成本。
6. 領域晚 tick 對新進敵人的整批傷害（2.4）在實戰中的觀感；純邏輯確定，量級要看 `MultDot` 與 B_max。
