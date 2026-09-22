# 審查：在實戰中靜默不觸發的機制（亡者歸來／化灰以外）

- 審查時間：2026-09-19 08:07（Asia/Taipei）
- 審查對象：`.codex\pre-fix14-snapshot\src\*.psc`、`.codex\pre-fix14-snapshot\plan-tree-nodes.json`（唯讀快照，未讀 live `src\`）
- 設計真相：`元素魔戰士規劃-v0.3.md`；已記錄的偏離：`實作紀錄.md`
- 實機證據：`.codex\smoke4-Papyrus.0.log`（只 grep `[ESSB]`）
- 範圍：只找「觸發條件假設了引擎與正常玩法不會產生的順序／歸屬／狀態／時機」的機制。亡者歸來與化灰那一對另有人在修，本文不重覆；但第 2 項與它們同根，修法必須一起涵蓋。
- 方法限制：沒有進遊戲、沒有建置、沒有讀 ESP／`build_v03.py`（不在快照內）。凡是要靠 MGEF 旗標或引擎行為才能定案的，一律標 medium／low。

## 先講這場 log 的實際樣貌（後面每一項都會引用）

| 項目 | 數字 | 來源 |
|---|---|---|
| 被接受的有效命中 `[Hit][L2]` | 39 | 全部 element=9／10，weapon=0／5 |
| 被拒的命中 `reason=invalid-actor` | 227 | 全部 weapon=5；其中含 power 位元（65536）的 6 筆、含潛行位元（2048）的 0 筆 |
| 擊殺 `[Kill][L1]` | 33 | 多數目標在 log 裡沒有任何被接受的 Hit，只有一筆 `invalid-actor` 拒絕，之後就是 Kill（例：`07:40:51AM … target=529149 reason=invalid-actor … flags=65632` → `07:40:52AM [ESSB][Kill][L1] 529149 element=10`；`07:44:13AM … target=-16685529 … flags=65536` → `07:44:16AM [ESSB][Kill][L1] -16685529 element=10`）。也就是這一場絕大多數敵人是一刀死，這一刀在腳本看到時目標已經死了 |
| 終焉 `[End][L1]` | 8 | element=10 reason=2 ×4、element=10 reason=1 ×1、element=9 reason=2 ×3；**reason=0（被切掉）0 次** |
| 融斷 `[Burst][L1]` | 7 | 6 次 `targets=0`，1 次 `targets=1` |
| 死咒結算 `[deathcurse]` | **0** | 8 次終焉裡 5 次是黑暗（每一次都會下死咒） |
| 同調最高 | `sync=13` | 三段門檻 30 從未到達 |
| 控制器 tick 間隔（由 `[env][L3]` 推算，該行需要 tick 且距上次 ≥5 秒） | 5–8 秒佔 37 次；11–34 秒佔 18 次 | 形態開啟中也一樣，例：`07:36:58` → `07:37:25`（27 秒，水形態開著）、`07:43:10` → `07:43:37`（27 秒） |
| 狀態宿主 tick 間隔 | 同一目標 `-16685521` 的 `[status][L3]` 只在 `07:43:42AM` 與 `07:43:50AM` 各一次，該目標從 07:43:26 活到 07:43:54 | 每秒 tick 實際上約 8 秒一次 |
| 關形態到融斷結算的延遲 | `07:44:46AM [Form][L1] close 10` → `07:45:09AM [Burst][L1] targets=0 …`（23 秒）；`07:44:31` → `07:44:44`（13 秒） | `CloseForm` 與 `OnFormClosed` 是同一條同步呼叫鏈 |

---

## 1. 發現（依實戰傷害程度排序）

### 1.1 死咒（含饕餮／處刑／亡魂／不治）在實戰中從未結算 — 信心：high

**檔案／行**
- `ESSBReactions.psc:359-369`（`EndDark`）：`akStatus.SetDeathCurse(3, amount, curseMult)` 或 `akCtl.SetDeathCurseOn(akTarget, 3, amount, curseMult)`
- `ESSBStatus.psc:905-923`（`Tick`）：`DeathCurseLeft -= 1`，歸零那一次才 `Ctl.ApplyDamage(10, amount, Holder)` 並呼叫 `ESSBElem3.AfterDeathCurse`
- `ESSBStatus.psc:748-752`（`OnUpdate`）：`If Holder.IsDead() … Return`，宿主一死就不再排程
- `ESSBController.psc:3540-3546`（`Tick`）：目標 `IsDead()` → `CaptureDeath` → `ClearSlot`；`ClearSlot` → `ClearPendingState`（`5671-5688`）把 `PendingCurse[aiSlot] = 0`，尚未綁定宿主的死咒直接丟棄
- `ESSBElem3.psc:646-681`（`AfterDeathCurse`）：饕餮、處刑、亡魂都只在這裡

**設計文字**（規劃 2.6）：「死咒：3 秒後對目標一次暗傷 = B_max ×2.0 + 目標已損失生命的 15%；死咒期間目標無法被治療」；5.12「饕餮：死咒結算時吸血吸魔各 B_max ×1.0」「處刑：死咒結算時目標生命低於 15% 則直接死亡」「亡魂：死咒殺死目標時，附近敵人恐懼 2 秒」。

**為什麼實戰不會發生**
1. 黑暗是這位玩家的主元素而且不切換。依 2.6，同元素只刷新印記不反應，所以黑暗終焉只會在三種時刻發生：按 Z 融斷、印記自然過期、或（見 1.7）目標死亡時印記被引擎移除。三者都發生在目標已死或即將死的時刻。
2. 倒數是「宿主 tick 次數」不是秒：`DeathCurseLeft` 只在 `ESSBStatus.Tick` 減一，而 log 顯示宿主 tick 約 8 秒一次（上表）。`deathcurse=5`（`DurationInt(3)` 乘了持續倍率）等於 40 秒左右的真實時間。
3. 目標在 1–3 刀內死亡。死亡後宿主停 tick（`OnUpdate` 的 `IsDead` 早退），控制器 `Tick` 又把格子清掉。

**log 證據**
```
[09/19/2026 - 07:43:50AM] [ESSB][status][L3] -16685521 heat=0 freeze=0 bleed=0 poison=0 astral=0 curse=1 holy=0 wet=0 fissure=0 catalyze=0 deathcurse=5 pressure=0 starlock=0 wetlock=0
[09/19/2026 - 07:43:50AM] [ESSB][End][L1] -16685521 element=10 reason=1 mult=1.123600
[09/19/2026 - 07:43:54AM] [ESSB][Kill][L1] -16685521 element=0
```
整場 `[ESSB][deathcurse]` 0 行，`[End][L1] … element=10` 5 行。

**最小修法**：在 `ESSBController.CaptureDeath()`（或 `OnKillEvent` 進入時、以及 `ClearSlot` 之前）檢查 `RegStatus[slot].HasDeathCurse()` 或 `PendingCurse[slot] > 0`，若有就立即結算固定項（`DeathCurseAmount × DeathCurseMult`）並呼叫 `AfterDeathCurse`（饕餮的回血回魔對玩家仍有意義；處刑對已死目標略過）。另把 `DeathCurseLeft` 改成以 `Utility.GetCurrentRealTime()` 的到期時戳判斷，不再數 tick。

### 1.2 連殺／奇襲／潛行風附傷／風勢直接滿：全部依賴「致命那一擊」被接受 — 信心：high（程式路徑）；本場 log 沒有潛行攻擊，無直接實機證據

與亡者歸來同根（`OnWeaponHit` 在目標已死時整段早退），但是不同機制，修那一對時要確認這裡一起被涵蓋。

**檔案／行**
- `ESSBController.psc:1429-1434`：`targetActor.IsDead()` → `LogRejectedHit("invalid-actor" …)` → `Return`
- `ESSBController.psc:1461-1468`：`sneak`／`power` 旗標與 `LastHitPower`／`LastHitSneak` 在上面那個早退**之後**才寫入
- `ESSBController.psc:1578-1580`（`ApplyProc`）：`If aiElement == 5 && abSneak → magnitude × SneakMult × KillStreakMult`
- `ESSBController.psc:1673-1676`（`ElementHitHook`）：`If LastHitSneak → SetSelf(3, WindThreshold)`
- `ESSBElem2.psc:307-314, 335-338`（`OpenWind`）：奇襲 `ESSBNodes.Br(akCtl, 4, 1, 2, 1) && akCtl.LastHitWasSneak()`
- `ESSBElem2.psc:1004-1007`（`OnKill`）：連殺 `aiElement == 5 && … && akCtl.LastHitWasSneak()` → `KeepSneak(5)`
- `ESSBElem2.psc:1085-1090`（`KillStreakMult`）：`TakeKillStreak()` 只在下一次**被接受的**潛行附傷才消耗

**設計文字**：1.1「潛行攻擊時風附傷 ×3，且風勢直接滿」；5.7 奇襲「潛行攻擊的開印同時觸發終焉（一刀開印兼吹飛），且不拉近」；5.7 連殺「潛行攻擊擊殺後 5 秒內不解除潛行，下一次潛行攻擊附傷 ×2 並重置奇襲」。

**為什麼實戰不會發生**：潛行攻擊在引擎裡本來就是 ×3～×6 的物理傷害，正常玩法下多半一刀致死。致命的那一刀到腳本手上時 `IsDead()` 已為真，於是：風的 ×3 附傷不施放、風勢不補滿、奇襲不觸發（連印記都沒開）、`LastHitSneak` 沒被更新（還是上一刀的值）。接著 `OnKill` 讀到的 `LastHitWasSneak()` 是前一次非致命命中的旗標，連殺只在「前一刀剛好也是潛行且沒殺死」時成立；而 `KillStreakMult` 的 ×2 只會落在「下一次潛行攻擊沒有一刀殺死」的情況。設計把潛行寫成「風是潛行物理攻擊最強的元素」，實作卻只在潛行攻擊失敗時給加成。

**log 證據**：227 筆 `invalid-actor` 拒絕中有 6 筆帶 power 位元（`flags=65536`／`65632`），證明重擊致死那一刀確實被丟掉；本場沒有任何一筆帶 2048 的潛行命中，所以潛行本身無實機樣本。

**最小修法**：把 `LastHitPower`／`LastHitSneak` 的寫入與一個「最後一擊目標」的記錄移到 `IsDead()` 早退之前（旗標從 `aiHitFlagMask` 讀，不需要活著的目標）；`OnKillEvent` 改讀「該目標的最後一擊旗標」而不是全域的 `LastHitSneak`。若亡者歸來的修法是「致死那一擊仍走附傷／開印流程」，則風的 ×3 與奇襲會一併恢復，仍要確認 `KeepSneak` 的入口。

### 1.3 反擊（5.1 純武藝熟練分支）永遠不會加成 — 信心：high

**檔案／行**
- `ESSBGuard.psc:99-102`：`If abHitBlocked && ESSBNodes.Br(Ctl, 11, 0, 1, 0) → Ctl.SetRiposte(3)`
- `ESSBController.psc:359`（宣告 `Int RiposteLeft`）、`1154`（`SwitchForm` 清 0）、`3682-3684`（`TickTimers` 減一）、`3749`（`TimersActive`）、`4676-4679`（`SetRiposte`）— **全部檔案裡沒有任何傷害路徑讀取 `RiposteLeft`**。`ApplyProc` 的註解（`1581`）寫著「反擊…下一次命中傷害 +30%」但下一行直接進 `If abOpening`，沒有乘 1.3；`ESSBNoForm.OnMartialHit`／`ApplyNoFormBaseline` 也沒有。
- 即使加回 `ApplyProc` 也到不了：反擊是無元素樹分支，`ESSBNodes.Br` 在 `FormActive == 1` 時對樹 11 路線 0／1 一律回 False（`ESSBNodes.psc:79-82`），而 `ApplyProc` 只在形態開啟時執行。

**設計文字**（5.1）：「反擊：格擋成功後 3 秒內下一次命中傷害 +30%」。`實作紀錄.md:821` 記為 FIXED：「`abHitBlocked` → `SetRiposte(3)`，下一次命中 `ApplyProc` 乘 1.3」— 快照裡沒有這半句。

**最小修法**：在 `ESSBController.OnNoFormHit`（`1615`）開頭取 `Bool riposte = RiposteLeft > 0`，成立就把 `ApplyNoFormBaseline` 的 `amount` 與 `ESSBNoForm.OnMartialHit` 內的真傷各乘 1.3，然後 `RiposteLeft = 0`。

### 1.4 神佑（5.9 持續傳奇分支）的觸發條件在引擎裡不可能成立 — 信心：high（致命傷路徑）

**檔案／行**：`ESSBGuard.psc:89-97`
```
If player.GetActorValue("Health") <= 1.0 && Ctl.TakeDivineSave()
    Ctl.ApplyUtil(4, 1.0, 0, player)
    Ctl.SetGuardDivine(2)
```
`TakeDivineSave`（`ESSBController.psc:4742-4748`）另外要求同調三段。

**設計文字**（5.9）：「神佑：同調三段時致命傷改為留 1 血並清除所有負面，每場戰鬥一次」。`實作紀錄.md:1020-1023`（決定 71.12）記錄的偏離只改了**效果**（補 1 血 + 2 秒受傷 ×0），沒有改**觸發**。

**為什麼實戰不會發生**：PO3 的受擊事件在引擎已經套用傷害之後才送出，再加上本場量到的多秒延遲。致命傷落地的那一刻玩家生命是 0，遊戲進入死亡流程（玩家沒有倒地待救），腳本永遠看不到「≤1 且活著」；非致命傷則不會把生命打到 ≤1。也就是這個分支只在「一擊剛好把生命打到 0 < HP ≤ 1」這種極端情況才會動。無敵視窗（`GGuardDivine` 給 PERK 0x24 ×0）是在腳本跑到之後才開，救不到觸發它的那一擊。

**最小修法**：把「留 1 血」改為事前武裝：PERK 進入點 0x24 ×0 加條件 `GetActorValuePercent(Health) < 門檻（例如 0.15）`、`ESSB_SyncStage >= 3`、以及一個「本場戰鬥已用」全域變數；腳本端只負責在受擊事件裡看到生命 < 門檻時記帳（設已用旗標、補 1 血），脫戰重置照舊。

### 1.5 雷電「被切掉」的終焉永遠放 0 電荷（放電／雷殛／餘電／過載終焉在切換路線全滅） — 信心：high（程式）；設計本身互相矛盾

**檔案／行**
- `ESSBController.psc:1146-1201`（`SwitchForm`）→ `1196-1198` 呼叫 `OnFormSwitched` → `ESSBController.psc:1260`：`ClearSelfAll()` → `3264-3268`：`SelfCharge = 0`
- 舊雷印記的切掉終焉發生在**之後**的第一下命中：`OnValidHitInternal`（`6633-6638`）→ `InstallMark`（`1720-1725`）→ `EndMark(aiSlot, 0, 1.0)` → `ESSBReactions.End`（`162-167`）`snapshot = akCtl.GetSelf(1)` 此時已是 0 → `EndShock`（`248-257`）`If charge <= 0 Return`
- 連帶：`ESSBElem.OverloadMult`（`718-723`）讀 `GetSelf(1) >= 8`；`EndShockNodes` 雷殛（`694-710`）`charge > 0` 才做；餘電 `SetPendingDischarge` → `AfterOpen`（`2030-2033`）`Discharge(Self, akTarget, GetSelf(1), …)` 也是 0。

**設計文字**：2.6「被切掉：切換元素後的第一下同時發生兩件事，先舊元素終焉，再新元素開印」、「主動結束仍然比較好：融斷有同調倍率，切換多一次開印」；2.6 表「放電：以你當前電荷數 × 30% B_max 對目標放電」；2.3「疊在你身上的狀態，離開形態（切換或關閉）時清空」。前兩條要「切換收割」，第三條在切換那一刻就把要收割的資源清了。`實作紀錄.md` 沒有把這個取捨記成偏離。

**為什麼實戰不會發生**：三拍節奏「鋪場 → 換元素收割 → Z 融斷」的第二拍，對雷來說是空的；只有 Z 融斷（`OnFormClosed` 在迴圈之後才 `ClearSelfAll()`，`1304-1343`）和留在雷形態等 8 秒過期才有電荷。

**最小修法**：`OnFormSwitched` 在 `ClearSelfAll()` 之前存 `SwitchCharge = SelfCharge`；`ESSBReactions.End` 在 `aiReason == 0 && aiElement == 3` 時用 `SwitchCharge` 當快照並清掉（一次性），`OverloadMult`／`EndShockNodes` 同樣接受快照參數（`EndShockNodes` 已有 `aiCharge` 參數）。

### 1.6 「秒」的兩套時鐘：以 tick 計數的視窗在負載下被拉長數倍，以真實時間計的狀態則整批瞬間過期；融斷因此常常打空 — 信心：medium-high（log 證據強；「缺陷」在於規格寫秒、實作數 tick）

**檔案／行**
- 以 tick 計數：`ESSBStatus.psc:830-836`（浮空 `AirLeft`）、`773-794`（血／毒／星痕環狀桶 `RingAge`，星痕「2 秒」= 2 tick）、`777-782`（催毒）、`852-854`（星鎖）、`905-923`（死咒）；`ESSBController.psc:3610-3734`（`TickTimers` 全部秒計時器：熔身、餘燼、淬火、疾電、殘影／神佑／披風／影身／預知／星光視窗、順勢、反擊、接管加成、連殺潛行、雙斷、同調保留、`OpenBoost`／`EndBoost`）、`3556-3566`（化身冷卻 `AvatarLeft`）、`3511-3520`（雷雨充電 `StormCharge`）、`4266-4335`（領域 `DomainLeft`）
- 以真實時間：`ESSBStatus.psc:800-850`（熱度 6 秒、冰封 3 秒、凍結 6 秒、裂痕／聖印／浸濕／水壓／詛咒 8 秒）；`ESSBController.psc:3502-3531`（風勢 5 秒、電荷 10 秒、戰意 5 秒、連段 4 秒）、`3547-3552`（印記 `RegUntil`）

**設計文字**：2.3 的持續／衰減欄全部以秒為單位；2.5「關閉形態的瞬間…一次結清」；1.1.1「腳本處理…同一個腳本幀內完成」。

**實戰上發生什麼**：本場控制器 tick 常見 8–12 秒、最長 34 秒，宿主 tick 約 8 秒一次（見開頭表）。於是（a）浮空 2 tick ≈ 16 秒才結算落地傷害、星痕 2 tick、死咒 3–5 tick，目標早死；（b）殘影／影身／水鏡等「2 秒」無敵視窗其實開 10 幾秒（反向，對玩家有利但不是設計）；（c）反過來，熱度／詛咒／冰封這些真實時間狀態在下一次 tick 才被檢查，一次 tick 落後 8 秒就整批歸零——冰封 3 秒的視窗可以在兩個宿主 tick 之間整個消失，`OnFrozenTick` 的強減速一次都不跑；（d）融斷：`CloseForm` 到 `OnFormClosed` 相隔 13–23 秒，7 次融斷 6 次 `targets=0`。融斷打空另一半原因是目標壽命短於印記壽命，這一半屬平衡不屬缺陷。

**log 證據**
```
[09/19/2026 - 07:44:46AM] [ESSB][Form][L1] close 10
[09/19/2026 - 07:45:09AM] [ESSB][Burst][L1] targets=0 outofrange=0 stage=1 k=1.590000 radius=1050.000000
[09/19/2026 - 07:43:42AM] [ESSB][status][L3] -16685521 heat=0 … deathcurse=0 …
[09/19/2026 - 07:43:50AM] [ESSB][status][L3] -16685521 heat=0 … deathcurse=5 …
```
`[env][L3]` 相鄰行間隔：29、15、21、27、11、12、12、34、12、11、16、11、27、12、11、17、12、11 秒（皆 ≥ 11 秒者）。log 裡沒有任何 `overstressed`／`Suspended stack` 警告，所以這是 VM 排程延遲，不是錯誤。

**最小修法**：所有「N 秒」視窗改存到期時戳（`Utility.GetCurrentRealTime() + N`），tick 只做「到期就結算」，這樣 tick 慢只會晚結算、不會拉長；真實時間狀態的「過期」則在讀取點（`GetStack`／`OnFrozenTick`）改為「先結算、再過期」，避免整批消失。負載本身（每次拒絕命中都走 `ResolveHitWeaponType`＋L3 字串、`NoteDamageElement` 的 128 格線性掃描、`TREES`／`env` L3）另案處理。

### 1.7 擊殺時讀狀態層數的機制：詛咒沒有快照，且全部依賴狀態宿主在目標死亡後仍然存活 — 信心：medium（宿主 MGEF 旗標不在快照內）

**檔案／行**
- `ESSBController.psc:5356-5368`（`CaptureDeath`）：只快照 `element/freeze/bleed/poison`；**沒有 curse**
- `ESSBController.psc:5391-5415`（`OnKillEvent`）：格子還在就 `GetStack` 現讀；格子不在就用快照
- `ESSBElem3.psc:1178-1187`（`OnKill`）：`Int curse = akCtl.GetStack(akTarget, 10)` 現讀 → 收割 `ApplyUtil(5, 15.0 * curse …)`、`Reanimate(akCtl, akTarget, curse)` 的亡者強化
- `ESSBController.psc:2342-2355`（`GetStack`）：`RegStatus[slot]` 為 None 時回 `PendingStacks`（清過就是 0）
- `ESSBStatus.psc:100-108`（`OnEffectFinish`）→ `OnStatusFinish`（`2298-2313`）：`RegStatus[slot] = None`

**設計文字**（5.12）：「收割：詛咒目標死亡回魔」「亡者強化：復生的僕從繼承死前的詛咒層數作為攻擊加成」；5.8 飲血／血承／不死、5.10 蔓延、5.4 連鎖冰封同樣是「X 目標死亡時」。

**為什麼實戰會失敗**
1. 確定的部分：控制器 `Tick` 先於 `OnActorKilled` 處理時（tick 與擊殺事件在不同腳本的佇列上，順序不保證），`ClearSlot` 之後 `GetStack(akTarget, 10)` 一定是 0，收割與亡者強化拿到 0；血／毒／凍結有快照所以還好。
2. 依賴引擎的部分：Skyrim 預設在 actor 死亡時移除身上未標 `No Death Dispel` 的法術效果。若 `ESSB_StatusHostEffect` 沒有這個旗標，宿主在死亡當下 `OnEffectFinish` → `RegStatus = None`，之後不管誰先到，`GetStack` 都回 0，連 `CaptureDeath` 的快照也是 0——飲血、血承、不死、蔓延、連鎖冰封、收割、亡者強化全部一起失效。印記 MGEF 有同樣問題：log 裡 `529193` 在 `07:42:03AM` 被擊殺，`07:42:08AM` 才出現 `[End][L1] 529193 element=10 reason=2`，早於它的 12 秒印記到期，與「死亡時印記被引擎 dispel → `OnMarkFinish` → 當成自然過期結算」一致（這也是 1.1 裡黑暗終焉多半落在屍體上的機制）。

**最小修法**：`CaptureDeath` 補上 curse（與 heat／holy）；並在 `OnWeaponHit` 拒絕 `invalid-actor` 之前、或在 `ApplyTrackedDamage` 每次成功套用時，把該目標的層數快照進 `DeadActor` 環（不必等 tick）。同時確認／補上 `ESSB_StatusHostEffect` 與 11 個 `ESSB_MarkEffect_<X>` 的 No Death Dispel 旗標；若刻意不加，`OnMarkFinish` 應以 `akTarget.IsDead()` 分辨「死亡移除」與「自然過期」，不要對屍體跑終焉與 XP。

### 1.8 熔斷（5.3 關閉熟練分支「融斷後目標熱度保留」）是死程式碼 — 信心：high（程式）；影響 medium（需投 5 點）

**檔案／行**：`ESSBElem.psc:747-749` 定義 `KeepHeatOnBurst`，全部快照沒有任何呼叫者。`ESSBReactions.EndFire`（`236-238`）固定呼叫 `ESSBElem.Detonate(akCtl, akTarget, afMult, True)`，`Detonate`（`422-433`）在 `abConsume` 為真時 `SetStack(akTarget, 1, 0)`，只有猛爆分支（`Br(0, 2, 0, 0)`）能保留。

**設計文字**（5.3）：「熔斷：融斷後目標熱度保留」。

**最小修法**：`ESSBReactions.End` 把 `aiReason` 傳進 `EndFire`，`EndFire` 用 `abConsume = !(aiReason == 1 && ESSBElem.KeepHeatOnBurst(akCtl))`。

### 1.9 火葬與亡魂用「套用之後立刻讀生命 ≤ 0」判定擊殺 — 信心：low-medium（`DoCombatSpellApply` 是否同步結算未驗證，實作紀錄本身也列為未驗證）

**檔案／行**：`ESSBElem.psc:435`（火葬）`akTarget.GetActorValue("Health") <= 0.0` 緊接在 `ApplyDamage` 之後；`ESSBElem3.psc:671`（亡魂）同樣緊接在 `Execute`／`ApplyDamage` 之後。`ESSBController.ApplyTrackedDamage`（`5279-5294`）也用同一個假設決定要不要保留 `LastDamage`。

**設計文字**：5.3「火葬：爆燃擊殺的目標對附近敵人再爆一次 ×0.5」；5.12「亡魂：死咒殺死目標時，附近敵人恐懼 2 秒」。`實作紀錄.md:1407-1409`（決定 82.12）已註明「和火葬是同一個時序問題…最壞情況是漏觸發」。

**為什麼可能永遠不觸發**：若法術效果的生命扣除要等下一個遊戲幀（Papyrus 原生呼叫回到 VM 時目標生命尚未更新），這個檢查永遠是 False。亡魂另外還疊在 1.1 上（死咒本身不結算）。

**最小修法**：改用擊殺事件：在 `Detonate`／`AfterDeathCurse` 記下「此目標剛被爆燃／死咒打過」（時戳＋元素），由 `OnKillEvent` 在 1 秒內看到該目標死亡時補做範圍效果。這與亡者歸來的歸屬修法是同一個掛勾。

### 1.10 斷咒（5.1 破魔熟練分支）判定的是「事件處理當下」是否施法，不是被打中當下 — 信心：medium

**檔案／行**：`ESSBNoForm.psc:184`：`If ESSBNodes.Br(akCtl, 11, 1, 1, 0) && IsCasting(akTarget)`；`IsCasting`（`239-254`）逐槽呼叫 `PO3_SKSEFunctions.IsCasting` 讀目標的**現在**狀態。

**設計文字**（5.1）：「斷咒：命中施法中的敵人打斷其施法，每 5 秒一次」。

**為什麼實戰很少成立**：本場 `OnWeaponHit` 的處理落後事件 5 秒以上（例：`529193` 的 `[Kill]` 在 `07:42:03AM`，該目標更早那一擊的 `[Hit][L2]` 卻印在 `07:42:04AM`；`[Hit]` 行印在事件本體最後）。法術施放動作只有零點幾秒到兩三秒，命中時在施法的敵人到腳本判定時多半已放完。fix round 13 把 graph 變數換成 PO3 `IsCasting` 修的是「讀不到」，沒有修「讀得太晚」。

**最小修法**：沒有可靠的「命中當下」施法旗標可傳，可退而求其次：在破魔印 AME 的動畫事件（已為反咒註冊的 `MRh_SpellFire_Event`／`MLh_SpellFire_Event`，`ESSBController.psc:2535-2559`）把「最近一次施法時戳」記在目標上，`OnManaBreak` 改判「命中前 1.5 秒內有施法事件」。

---

## 2. 檢查過、認為在實戰中會正確觸發（或不觸發是設計所定）

- **印記的開印／終焉／刷新**：`ApplyMark`（`1744-1803`）在重套前把 `RegMark[slot] = None`，`OnMarkStart`／`OnMarkFinish`（`2194-2226`）只認登記的實體，所以不管引擎對同法術重套是「換實體」還是「同實體續時」都不會誤報終焉；`TakeEndSlot` 1 秒冷卻讓 tick 過期與 AME finish 只結算一次。
- **融斷路徑的自身資源**：`OnFormClosed`（`1287-1344`）先跑 `EndBothMarks` 迴圈才 `ClearSelfAll()`，所以雷斷（`ShockBurstBonus`）、洩壓（`VentMult`）、放電在 Z 融斷時讀得到電荷／過熱；只有切換路線壞掉（1.5）。
- **風勢→風刃**：`ElementHitHook`（`1661-1680`）在同一次命中裡 `CheckWindGauge`，不靠 tick。
- **餘燼／淬火／免門檻／連斷／雙斷／永續**：在 `ESSBNoForm.OnBurst`／`OnFormClosed` 設定、在下一次開形態或無形態命中消耗，順序正確。
- **水的導引在過期時仍給 +5 同調**：`EndWater`（`350-355`）只把接管倍率限制在 reason 0，同調照給；log `07:36:54AM [Sync][L1] stage=1 value=7 element=9` 緊接 `[End][L1] 112452 element=9 reason=2`，與 2.6「過期…沒有 K_sync，也沒有接管元素」一致。
- **夢魘**：`[Fear][L1]` 5 行，開印時確實施放；`CanCharm` 的等級上限與免疫名單合理。
- **環境加成**：`OnWaterHit`（`ESSBElem3.psc:236`）同時看 `IsWet || IsEnvWet`；霜結與冰命中吃 `IsEnvStormy`；夜／晝進 `GetDamageMult` 與星界 `Range`。
- **反咒**：註冊在穩定 alias 上（`StartCounter`／`OnAnimationEvent`），事件驅動，不受 tick 延遲影響。
- **血引／聖引的 pending**：`SetPendingBleed`／`SetPendingHeal` 在 `ESSBElem2.psc:371`／`405` 的 `OpenBlood`／`OpenDivine` 被消耗。
- **宿主未綁定的重試**：`SwapHosts`（`2391-2399`）對 `RegHostPending` 超過 3 秒的格子會重新 `EnsureStatus`，不會永久卡在 pending。
- **冰的過期碎冰永遠是「未冰封 ×1.0」**：印記 8 秒、冰封 3 秒後歸零、凍結 6 秒未命中歸零（2.3），所以自然過期時一定沒冰封。這是設計自洽的（2.6 說過期只是保底），但對像本場這種不切元素的玩法，碎冰處決只剩「冰封後 3 秒內按 Z」一條路。
- **冰封融斷分支**：`FrostBurstShatter`（`ESSBElem.psc:752-754`）沒有呼叫者，但 `EndFrost` 本來就對所有終焉跑 `Shatter`（含處決），所以分支是多餘的，不是漏掉的。
- **定神／御風／冰原的「免疫減速」**：`ESSBNodes.SelfSlowImmune`（`333-342`）沒有呼叫者；不過全部 24 處 `ApplyUtil(0, …)` 的目標都是敵人或攻擊者，本模組從不減玩家速度，所以沒有東西可免疫，無實戰損失。
- **所有需要 reason 0（被切掉）的接管類效果**（導引倍率、星落開印 ×1.5、餘燼 ×1.5、寒留、順勢、血引、聖引、蝕魔終焉、星引、星界之門、協奏、大協奏、三重奏、餘響）：本場 0 次 reason 0，因為玩家沒有在活著的印記上切換元素。這是設計要求的操作，不是程式缺陷；但它們與 1.5 一樣，都建立在「目標活得過切換」上。
- **同調三段門檻**：本場最高 `sync=13`，所有「同調三段時」節點都到不了；是平衡問題（TTK、每次關形態歸零），不屬本審查範圍。

---

## 3. 不進遊戲無法確認的事

1. `ESSB_StatusHostEffect`、`ESSB_MarkEffect_<X>`、`ESSB_ManaBreakEffect` 的 MGEF 旗標是否含 No Death Dispel（0x00200000）。ESP 與 `build_v03.py` 不在快照裡；1.7 的第二半與 1.1 的「終焉落在屍體上」都取決於它。
2. `Actor.DoCombatSpellApply` 對 Contact 法術是否在原生呼叫返回前就扣完生命（1.9、`ApplyTrackedDamage` 的保留邏輯都依賴這一點）。
3. PO3 `OnActorKilled` 是在 `kDying` 還是 `kDead` 送出、以及 DoT（放血／毒）致死時 `akKiller` 是否回玩家；log 裡 `112452` 在 `07:36:24AM` 與 `07:37:11AM` 各被「擊殺」一次卻在之間被正常命中，像是必要／受保護角色的倒地事件，需要確認 `OnKillEvent` 不會對倒地重複結算（`SettledDead` 八格去重在跨戰鬥時會被沖掉）。
4. PO3 `OnHitEx`（玩家受擊）對箭矢是否也回 `akProjectile = None`；若是，`ESSBGuard.psc:87` 的 `melee` 會把遠程當近戰（灼身／寒反／靜電／毒皮／殘影／影身會被箭觸發）。這是「多觸發」不是「不觸發」，列此備查。
5. 本場的 `ESSB_MultDuration` 實際值（`deathcurse=5` 暗示約 1.5），影響 1.1 的秒數估算但不影響結論。
6. `[Form][L1] close 10` 在 `07:43:31`／`07:43:51` 與 `07:44:31`／`07:44:46` 各成對出現而中間沒有 `switch`；`CloseForm`（`1203-1225`）沒有 `FormActive` 守衛，`ESSBFormRules.OnUpdate` 的魔力耗盡關閉（`ESSBFormRules.psc:114-123`）與玩家按 Z 可能在不同執行緒各跑一次。第二次融斷 `targets=0` 無害，但同調歸零與 `ESSBNoForm.OnBurst` 的餘燼／連斷會被第二次覆寫，需實機確認是否真的雙跑。
7. Papyrus VM 在本場的實際負載來源（哪一段呼叫吃掉時間）。1.6 只證明了 tick 與事件延遲的幅度，沒有證明原因。
