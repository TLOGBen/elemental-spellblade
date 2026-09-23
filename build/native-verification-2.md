# Native 能力查證（第二輪）：v0.4 §10.3 逐項 + 臨時血量／魔力／精力超上限

查證時間：2026-09-24（+08:00）。純研究，未改任何程式或設計文件。

## 0. 證據來源與方法

- CommonLibSSE-NG：`native/dependencies.lock.json` 鎖定 commit `b93280e832f263dbef44e44cbe2936622a02f91a`，本機副本 `native/deps/CommonLibSSE-NG/`。下文「`檔案:行`」都是指這個 commit。
- SKSE 2.0.20 原始碼：本機 `D:/Game/Other/SKSE/SkyrimSE/src/skse64/`（`skse64_common/skse_version.h` = 2.0.20）。
- 執行檔：`SkyrimSE.exe` 1.5.97，sha256 `5666E1BDDD01BCAB31ECF11691EF1A3F22E1541AF79F2BC0E55318533CFE5D12`。Address Library `version-1-5-97-0.bin` sha256 `1D7530D001139CA58F462EA0210A8055868159057BA8B5EBC624FC5E9C4F5E9A`。
- 工具：llvm-objdump 21.1.8（Intel 語法），加上在 repo 外暫存區寫的一次性 Python 腳本：解析 Address Library（照 NG `include/REL/ID.h:331` `unpack_file` 的格式）、用 numpy 找 call／RIP-relative 參照、用 Papyrus 註冊字串找 native thunk。腳本不放進 repo；下文每一條結論都附上 VA 和 Address Library ID，可以用 round 19 的 `build/fix19_binary_evidence.py` 同樣的方式重現。
- 沿用 round 19（`build/native-verification.md`）已經查證的部分，不重做：TESHitEvent 結構、`CastSpellImmediate` 路徑（0x14054C5F0 → 0x14054CD10）、effectiveness 1.0、套用 visitor 0x140551980 的強度覆寫。
- 「UNCONFIRMED」表示原始碼和二進位都不足以下定論，同一段會附上能判定的遊戲內探針。

## 1. 所有事件共通的性質（每個事件項目都會用到）

- **同步通知，不能取消遊戲行為。** `BSTEventSource<T>::SendEvent`（`include/RE/B/BSTEvent.h:89-121`）持有 spinlock，依序呼叫各個 sink；sink 回傳 `kStop` 只會中斷**後面其他 sink**（`BSTEvent.h:106-108`），不會取消引擎的動作。我們的 sink 一律要回 `kContinue`，否則會吃掉其他模組的事件。
- ScriptEventSourceHolder 是 static 物件（0x141EBF7B0，getter ID 14108 = 0x140186790）；各事件來源的位移見 `include/RE/S/ScriptEventSourceHolder.h:64-119`（死亡 0x370、命中 0x5D8、效果套用 0x738、效果套用／移除 0xB0、施法 0xE18）。
- **在哪個執行緒送出：UNCONFIRMED。** 下面各事件都查到了 sender 函式，但這些函式本身（命中、KillImpl、AddTarget、SpellCast）由誰、在哪個執行緒呼叫，靜態分析沒辦法完整追出。round 19 的命中 sink 目前直接在 sink 裡呼叫 `CastSpellImmediate`。建議做法：sink 裡只讀資料、記帳；會寫入遊戲狀態的動作（改 AV、Dispel、InterruptCast、放置物件）一律丟 `AddTask`。探針 P1 可以確認執行緒。

---

## 2. DLL 每秒執行點

**判定：YES**。做法是「背景計時執行緒 + 每 tick 一次 `AddTask`」。**不能**讓 AddTask 在 task 裡重新排自己。

API：
- `SKSE::GetTaskInterface()`（`include/SKSE/API.h:24`）→ `TaskInterface::AddTask(TaskFn)`（`include/SKSE/Interfaces.h:196`，實作 `src/SKSE/Interfaces.cpp:166` = `new Task(fn)` 交給 SKSE 的 `AddTask`）。
- 暫停判定：`RE::UI::GetSingleton()->GameIsPaused()`（`include/RE/U/UI.h:83`，實作 `numPausesGame > 0`）。退出判定：`RE::Main::GetSingleton()->quitGame`（`include/RE/M/Main.h:77`）。可選的幀時間：`RE::GetSecondsSinceLastFrame()`（`include/RE/M/Misc.h:23`）。

證據：
- SKSE 2.0.20 `skse64/Hooks_Threads.cpp`：`BSTaskPool::ProcessTasks` 先跑原本的 `ProcessTaskQueue_HookTarget`，接著用 **`while (!IsTaskQueueEmpty())`** 把佇列一直取到空為止。所以 **task 在 `Run()` 裡再 `AddTask` 自己的話，同一個迴圈會馬上再取出來執行，變成同一幀內的無窮迴圈，遊戲卡死**。SKSE 的 UI 佇列（`Hooks_UI.cpp` `ProcessCommands`，`while (!g_uiQueue.empty())`）也有一樣的問題。「每幀 task 自我重排」這條路因此排除。
- 取出佇列的位置：SKSE 把 `Main::Update`（ID 35565，0x1405B2FF0）+0x6B8 的 call（0x1405B36A8 → `BSTaskPool::ProcessTaskQueue` ID 35916，0x1405C1BE0）改成自己的 ProcessTasks；第二個位置是 0x1405B44C0（ID 35582）+0x1C，由 ID 38136 呼叫（推測是載入畫面期間的更新）。`Main::Update` 開頭唯一會跳過這段的分支，是 0x1405B3013–0x1405B3036 的 `GetAsyncKeyState(VK_TAB)` + `VK_MENU`（Alt+Tab）。所以**每幀都會在主執行緒取佇列，選單開著時也照樣執行**。

建議實作：
1. 資料載入後開一條 `std::thread`（或 Win32 threadpool timer），每 100 ms 到 1000 ms 醒來一次，只做一件事：`AddTask(tick)`。用 atomic 旗標避免重疊：上一個 tick 還沒被執行就不再排。
2. `tick()` 在主執行緒執行：先確認玩家存在、3D 已載入、不在 `kPreLoadGame`→`kPostLoadGame` 之間；遊戲暫停（`GameIsPaused()`）時只重設時間基準、不算時間；再用 steady_clock 差值（或累加的幀時間）換算成遊戲秒數，然後跑每秒邏輯。
3. 看到 `Main::quitGame` 就停掉計時執行緒；執行緒 detach，不在 DLL_PROCESS_DETACH 裡 join。

代價：每 tick 一次 `new std::function` 加一次 critical section。SKSE 本來就每幀檢查佇列，額外成本可以忽略；10 Hz 也沒問題。

風險：佇列在載入畫面（第二個位置）也會執行，一定要有第 2 步的守門；關遊戲時計時執行緒可能晚一步呼叫 AddTask（用 quitGame 或 atomic 關閉，風險低）；別的模組的 task 很慢時，tick 會被延後，所以要用實際經過的時間計算，不要假設剛好 1 秒。

替代方案：既有的 Papyrus `RegisterForSingleUpdate` 每秒呼叫一個 DLL native（非 latent）。不需要新執行緒，但執行時機受 Papyrus 負載影響，native 在哪個執行緒執行也 UNCONFIRMED（探針 P1 一起確認）。

v0.4 的後備方案（放血改成命中時換算）不需要，除非探針 P2 失敗。

## 3. 效果移除事件

**判定：PARTIAL**。事件存在，但**只有附掛 Papyrus 腳本的 MGEF 才會送**。

API：`RE::TESActiveEffectApplyRemoveEvent { caster, target, activeEffectUniqueID(uint16), isApplied }`（`include/RE/T/TESActiveEffectApplyRemoveEvent.h:13-16`）。查效果：`MagicTarget::GetActiveEffectList()`（`include/RE/M/MagicTarget.h:84`）和 `ActiveEffect::usUniqueID`（`include/RE/A/ActiveEffect.h:113`）。

證據（ID 33317，0x14053FB60，ActiveEffect 的開始／結束流程）：
- 只有在 `effect->baseEffect->formFlags` 的 bit 22（0x400000）有設、而且 target 不為 null 時（0x14053FD56–0x14053FD5E），才會用 0x140540680 配一個 uniqueID 存到 +0x84。開始時經 0x1405415A0（ID 33346，holder+0xB0）送 `isApplied=1`（0x14053FDCE）；結束時只在 `usUniqueID != 0` 時送 `isApplied=0`（0x140540000–0x140540069）。
- 整個 `.text` 裡唯一會設這個 bit 的地方是 0x140907416（ID 52730，Papyrus VM 把 VMAD 腳本綁到 form 上的程式碼）。所以**沒有腳本的 MGEF，套用和移除都不會送這個事件**。這一點由二進位推定，探針 P3 確認。
- 送出時，ActiveEffect 還握在呼叫端手上。移除事件送出當下它是否還在目標的清單裡：UNCONFIRMED。

建議做法：
- 我們自己的 MGEF 掛一個空的 stub 腳本就能讓事件出現（Papyrus 成本只剩綁定，沒有事件處理）；套用時記下 `uniqueID → {MGEF, 目標, 我們的狀態}`，移除時用 uniqueID 查回來。
- 或者完全不用事件：在每秒 tick 輪詢自家 MGEF 還在不在（延遲不超過 1 tick）。
- 外部模組的效果通常沒有腳本，不能靠這個事件。

後備：v0.4 寫的「保留小支 Papyrus 到期回呼」仍然成立；但上面兩個做法任一個都可以取代它。

## 4. 死亡事件

**判定：YES**。

API：`RE::TESDeathEvent { actorDying, actorKiller, dead }`（`include/RE/T/TESDeathEvent.h:13-15`）；`Actor::GetKiller()`（`include/RE/A/Actor.h:550`，讀 `myKiller`，`Actor.h:654` 位移 0x100）。

證據：
- `Actor::KillImpl`（Actor vtable 0x10E，ID 36872，0x140603B30）：一開始先查 deferred kill（0x1406282C0），是的話轉 0x140628280，**不死亡、直接 return**（0x140603B94）。接著用 `a_attacker` 取 handle 寫入 `myKiller`（0x1406045A5；沒有 attacker 就寫 null handle），然後經 ID 37437（0x14061E370：holder+0x370，`dead=false`）在 0x14060499F **同步**送出事件。
- `dead=true` 那一次由 ID 37436（0x14061E2C0）送，呼叫它的是 ID 36723（0x1405FB640）。KillImpl 在 0x140605302 會呼叫 36723，另外還有 8 個呼叫點（ID 19374、36608、36614–36616、38384、38606、38607）。兩次事件的 killer 都讀 `myKiller`。
- 每次死亡會收到兩個事件（`dead` 分別是 false 和 true），sink 必須依 `dead` 去重。

風險：兩次事件、被 deferred kill 延後的死亡（見 §13）、sink 要回 `kContinue`。

## 5. 死亡事件的兇手欄位（瘋狂中的 NPC 擊殺時是否可靠）

**判定：PARTIAL**。欄位的來源確定，實際值取決於呼叫端傳進來的 attacker。

- 如 §4 所述，killer 就是呼叫 KillImpl 的人傳入的 `a_attacker`。傷害路徑的呼叫端是 `HandleHealthDamage(attacker, dmg)`（`Actor.h:458`，由 `RestoreActorValue` 0x1406212EF 帶入 attacker）。所以瘋狂中的 NPC **用武器或法術親手打死**目標時，killer 應該是那個 NPC。
- 目標如果是死於**我們（玩家）的持續效果**，或其他來源（詛咒 DoT、墜落、陷阱），killer 會是效果的施法者（玩家）或 null，**不是**瘋狂中的 NPC。
- 狂宴真正要的語意是「瘋狂中的敵人**造成**的擊殺」。上面這個性質對它有利，但混合傷害（瘋狂 NPC 砍一刀，最後死於我們的 DoT）會判給玩家。
- UNCONFIRMED：瘋狂（Frenzy）狀態的 NPC 呼叫 KillImpl 時，attacker 參數在所有路徑上都有正確帶入。探針 P4。

後備（v0.4 寫的「瘋狂敵人自己死亡時視為帶黑暗印記」）維持可用。建議加一條折衷：killer 不為 null、不是玩家、而且身上有我們的瘋狂 MGEF → 視為狂宴。

## 6. 施法事件（施法者、法術、消耗魔力）

**判定：PARTIAL**。拿得到施法者和法術；事件沒有帶魔力消耗，但可以用同一個引擎函式算出來；**只有「放出」這個時點，沒有「開始施法」的時點**。

API：`RE::TESSpellCastEvent { object(施法者 ref), spell(FormID) }`（`include/RE/T/TESSpellCastEvent.h:13-14`）。消耗：`MagicItem::CalculateMagickaCost(Actor*)`（`include/RE/M/MagicItem.h:111` → `CalculateCost`，`include/RE/Offsets.h:372` ID 11213）；雙持：`MagicCaster::GetIsDualCasting()`（`include/RE/M/MagicCaster.h:67`）。

證據（`ActorMagicCaster` vtable 0x141637490 slot 9 = `SpellCast`，ID 33363，0x140542470）：
1. 0x1405425CF 呼叫 `CalculateCost`（0x140101A30 = ID 11213）算 `(spell, actor)`；
2. `GetIsDualCasting`（vfunc 0xB0）為真時經 0x1403C1720 調整；
3. 0x140542642 用 `RestoreActorValue(kDamage, av, -cost)` **先扣魔力**；
4. 最後 0x14054272C 經 holder+0xE18（0x140545040，ID 33428）送出 `TESSpellCastEvent`。

所以事件在**放出、扣完魔力之後**送。專注法術只有在開始時送一次，之後每幀扣的魔力不會再送事件。所有 actor 都會送。另外 ID 28336、28337、28595、28596（0x14042xxxx）也會送這個事件，推測是捲軸或其他路徑，未細查。

- 消耗估計：sink 裡呼叫 `spell->CalculateMagickaCost(caster)`，雙持時照引擎的雙持倍率乘上去（事件沒說是哪隻手，要查 `magicCasters[]` 的 `currentSpell`）。專注法術只能拿到每秒消耗。
- 逼近（「15 公尺內的敵人施法時」）：用放出時點可以做到。
- 反咒如果需要「敵人**開始**唸咒」的時點：這個事件做不到。可行替代：(a) 在 tick 輪詢附近敵人的 `magicCasters[i]->state`（見 §7）；(b) 對個別 actor 註冊 `BSAnimationGraphEvent` sink，聽 `BeginCastLeft/Right`（程式庫 API，不過要逐一註冊、管理生命週期）。

v0.4 的後備（逼近改成「受到法術傷害時」）不需要。反咒的後備改用 (a)。

## 7. 命中時讀取目標施法狀態

**判定：YES**。直接讀 actor 的施法器，不需要事件。

API：`Actor::GetActorRuntimeData().magicCasters[4]`（`include/RE/A/Actor.h:679`，唯讀，可能是 null）；`MagicCaster::state`、`currentSpell`、`castingTimer`（`include/RE/M/MagicCaster.h:89-91`；`State` 列舉在 `:29-40`）；`Actor::IsCasting(MagicItem*)`（`Actor.h:585`，ID 37810）；`Actor::WhoIsCasting()`（`Actor.h:641`，inline，讀 `currentSpell`）。**不要**用 `GetMagicCaster()`（vfunc 0x5C），它可能會建立新的施法器。

- 命中 sink 執行時，目標還沒扣血（見 §15），可以在 sink 裡同步讀。
- UNCONFIRMED：`State` 大半是 `kUnk`。哪幾個值代表「正在蓄力或唸咒」，CommonLib 只標了 `kCharging=5`、`kCasting=6`、`kReady=3`。探針 P5 會在 NPC 施法的每個階段記錄 state。

## 8. 中斷施法（安全的原生做法）

**判定：YES**。

API：`Actor::InterruptCast(bool a_restoreMagicka)`（`include/RE/A/Actor.h:577`，實作 `src/RE/A/Actor.cpp:727`，ID 37808）。

證據：Papyrus `ObjectReference.InterruptCast` 的 native（0x140994460，ID 55658）對 actor（formType 0x3E）呼叫 0x140631C80（= ID 37808），而且 `edx = 0`（不退魔力）；非 actor 則對其施法器呼叫 0x14054CB70。所以 **`Actor::InterruptCast(false)` 和 Papyrus InterruptCast 是同一條引擎路徑**，風險等同於 Papyrus 已經在用的東西。

用法：丟到 `AddTask` 在主執行緒呼叫。KillImpl 自己也會呼叫 37808（0x140604070），可見引擎內部也常用。

風險：對已經死亡或不在載入範圍的 actor 呼叫前，先檢查 `Is3DLoaded()` 和 `IsDead()`。

## 9. 效果套用事件與「施法得來、有持續時間、屬增益」的判定

**判定：PARTIAL**（事件）／**YES**（沖刷當下的判定）。

- `RE::TESMagicEffectApplyEvent { target, caster, magicEffect(FormID) }`（`include/RE/T/TESMagicEffectApplyEvent.h:13-15`）：由 ID 33742（0x140553750）在 0x14055388B 送出，呼叫它的是 `Actor` 的 `MagicTarget::AddTarget`（ID 37832，0x140633090，0x14063311E）和 ID 33918。**所有效果都會送，不需要腳本**；但送出時 **ActiveEffect 還沒建立**，只拿得到 MGEF，拿不到法術、持續時間或強度。前面的條件檢查（0x1405537B8 的 vfunc 0x58）失敗時不會送。
- `TESActiveEffectApplyRemoveEvent` 只有腳本 MGEF 才會送（§3）。
- **水壓沖刷用不著事件**：沖刷發生時，直接走訪目標的 `GetActiveEffectList()` 逐一判斷：
  - 「施法得來」：`ae->spell->GetSpellType()`（`MagicItem.h:80`）是 `kSpell`（也可以放寬到 `kScroll`、`kStaff`），而且 `ae->castingSource` 不是常駐能力（`ActiveEffect.h:115`）。
  - 「有持續時間」：`ae->duration > 0`（`:109`）。
  - 「屬增益」：`!base->IsHostile() && !base->IsDetrimental()`（`include/RE/E/EffectSetting.h:143-144`）。
  - 處理：`ae->Dispel(true)`（`ActiveEffect.h:90`），放在 AddTask 裡執行。
- 附帶發現（§10.4 的暫緩項目）：披風每一跳對鄰居施放的關聯法術也會走 AddTarget → 33742，所以候選做法 (a)「DLL 接效果套用事件，把那一劑併進中毒」可行，而且不需要腳本。

## 10. 多效果強度覆寫（一顆法術的多個效果分別給強度）

**判定：NO**（一次施放做不到）。

證據：round 19 的套用 visitor 0x140551980 對**每一個** ActiveEffect 都做 `magnitude = caster.magnitudeOverride`（`+0x3C`，非 0 才寫）。整次施放只有一個覆寫值（`MagicCaster.h:93`）。施放後再寫 `ActiveEffect::magnitude`（`ActiveEffect.h:110`）屬於寫入遊戲記憶體（違反規則），而且已經套上的 Value Modifier 不會跟著重算。

後備（**修正 v0.4**）：比「每層一顆 MGEF」更省的做法，是**把多效果法術拆成幾顆單效果法術，各自用 `CastSpellImmediate` 帶自己的覆寫值施放**（同一 tick 連續施放）。視覺特效只掛在其中一顆上。詛咒的五種抗性如果需要逐層的固定值，v0.4 的「每層一顆 MGEF」仍然可以用；但只要是「強度可以任意換算」的情況，拆法術就夠了。

## 11. 披風關聯法術的強度覆寫

**判定：PARTIAL**。可以透過披風自己的強度來控制，但**半徑會跟著改變**。

證據（`CloakEffect` vtable ID 257635 = 0x141637990，slot 4 `Update` = 0x140546390（ID 33463）→ 0x1405463D0）：
- 關聯物件是 `baseEffect->data.associatedForm`（MGEF+0x70），而且必須是 SPEL（formType 0x16）。
- **搜尋半徑 = 披風 ActiveEffect 目前的強度 × 21.333**（0x14053E120 GetMagnitude × 0x141637A98 的常數；也就是強度以呎為單位）。
- 對每個目標、關聯法術的每個效果，組一份 `MagicTarget::AddTargetData`（`include/RE/M/MagicTarget.h:56-72`），其中 **`magnitude`（+0x3C）= 披風目前的強度**（0x1405465F1–0x1405465F6），`castingSource = 3`，然後呼叫 `AddTarget`（0x14054660D）。

所以用 `CastSpellImmediate(..., magnitudeOverride=X)` 施放披風時，關聯法術收到的強度也是 X，但半徑同時變成 X × 21.33。
- UNCONFIRMED：`AddTargetData.magnitude` 對關聯法術的效果是「絕對覆寫」還是別的用法（AddTarget 核心沒有追完）。探針 P6。

後備：v0.4 的「多顆固定強度火源版本」維持。另一個選項是：披風強度固定當半徑用，傷害改由 DLL 每 tick 對範圍內的目標 `CastSpellImmediate` 帶覆寫值——這其實就是 §2 的每秒點取代披風。

## 12. 受擊時的原生推力／擊倒 API

**判定：YES**。

API：`AIProcess::KnockExplosion(Actor*, const NiPoint3& a_location, float a_magnitude)`（`include/RE/A/AIProcess.h:182`，實作 `src/RE/A/AIProcess.cpp:197`，ID 38858）；取 process：`actor->GetActorRuntimeData().currentProcess`（`Actor.h:651`）。

證據：Papyrus `PushActorAway` 的 native（0x140996340，ID 55682）在目標有 process、而且 0x140608DE0 回傳 0 時，以來源物件的座標（+0x54..+0x5C）和強度呼叫 0x14067D4A0（= ID 38858）。**和 Papyrus PushActorAway 完全同一條路**。KillImpl 也會呼叫它（0x140603EB2）。

用法：`AddTask` 裡執行 `if (auto p = target->GetActorRuntimeData().currentProcess) p->KnockExplosion(target, attackerPos, mag);`。那個 0x140608DE0 的前置檢查（推測是某種狀態，例如坐騎或家具）我們也要照做；它沒有 CommonLib 包裝，最保險的做法是先確認目標沒有騎乘、沒在使用家具、`!IsDead()`。
- UNCONFIRMED：0x140608DE0 的語意。探針 P7（對騎馬的 NPC 施加推力）。

v0.4 的後備（Papyrus 推力）不需要。

## 13. 神佑延遲死亡（StartDeferredKill）的 C++ 對等

**判定：NO**。

證據：Papyrus `StartDeferredKill` 的 native（0x14094DEB0，ID 53956）→ 0x140628260（ID 37662，`dl=1`）→ 0x1406820E0（ID 38973）。後者直接寫入 `MiddleHighProcessData` 的 +0x2F8（計數）、+0x332 `inDeferredKill |= 1`、+0x2D4 `deferredKillTimer`（`include/RE/M/MiddleHighProcessData.h:208, 254`）。
- CommonLib-NG 對這個函式**沒有任何包裝**（全庫 grep `DeferredKill` 只找到欄位）。
- 在 C++ 裡做同樣的事，只有兩種方式：寫那些欄位（寫入遊戲記憶體），或自己用 REL 呼叫一個 CommonLib 沒有提供的位址（不屬於程式庫 API）。兩者都違反規則。
- 行為面的證據：KillImpl 開頭檢查 deferred（0x140603B88）時直接 return，所以 deferred 期間不會有死亡事件；EndDeferredKill 之後才會真正死亡並送事件。

後備：留在 Papyrus（v0.4 的做法正確）。

## 14. 衝刺耐力消耗的入口

**判定：NO**（沒有進入點）。有 PARTIAL 的替代做法。

證據：`fSprintStaminaDrainMult`（Setting 在 0x141DE2528）、`fSprintStaminaWeightBase`、`fSprintStaminaWeightMult` 只有 0x1403C0A30（ID 25900）一個地方讀取，而呼叫它的只有 ID 36994（0x14060E820）：

`drain = (fSprintStaminaWeightMult × 裝備重量 + fSprintStaminaWeightBase) × dt × fSprintStaminaDrainMult`

裝備重量來自 `Actor::GetEquippedWeight`（`Actor.h:543`，ID 37333）。算出來後在 0x14060E907 用 `RestoreActorValue(kDamage, Stamina, -drain)` 扣掉。
- Skyrim.esm 的值是 7.0 / 1.0 / 0.02，也就是每秒扣 `7 × (1 + 0.02 × 裝備重量)`。
- **沒有 perk 進入點，也沒有 AV 乘數**。唯一會間接影響的是「Mod Armor Weight」進入點（0x20，在 ID 15883/15886 使用），它改的是裝備重量，只影響重量那一項，做不到 -50%。GMST 是全域設定，改了會影響所有 actor，不採用。

替代（PARTIAL）：
- (a) 純資料：一顆 ability，帶「回復耐力」的 Value Modifier（沒有 Recover，每秒回復），條件為 `IsSprinting == 1`，強度 ≈ 3.5 + 0.07 × 典型裝備重量。
- (b) DLL：在 tick 裡檢查 `player->AsActorState()->IsSprinting()`（`include/RE/A/ActorState.h:185`），依同一個公式回補一半：`RestoreActorValue(kDamage, Stamina, +0.5 × drain × dt)`。10 Hz tick 下很準。

兩者都是「補回來」，不是「少扣」。耐力降到 0 的那一刻仍然會觸發（0x14060E92A 設旗標）。v0.4 寫的「該半條不落地」可以改成 (b)。

## 15. 受擊事件當下能不能讀到這一擊實際扣掉的生命

**判定：PARTIAL**。在 sink 當下讀**不到**；要在 sink 記下扣血前的值，下一個 task 再讀扣血後的值，兩者相減。

證據：TESHitEvent 在三條路徑上都**比扣血早**送出：
- 近戰：ID 37650（0x140627930）在 0x140627C0D 呼叫會送事件的 ID 37674（0x140629090，送出點 0x1406296F7），之後才在 0x140627CBB 呼叫 ID 37673（0x140628C20），由它在 0x140628FFC 呼叫扣血函式 ID 36345（0x1405D6300）。
- 投射物：ID 42677（0x140739630）在 0x140739894 送事件，之後才建立 HitData（0x1407399CD）並在 0x140739A0C 呼叫 ID 37633（0x140626400，內含 36345 呼叫，0x140626797）。
- 法術：`AddTarget`（37832）在 0x140633206 送事件；傷害要到效果開始以後才發生。
- `MiddleHighProcessData::lastHitData`（`MiddleHighProcessData.h:158`；`HitData::totalDamage` 在 `include/RE/H/HitData.h:63`）在 sink 當下還沒填入，或還是上一擊的值，不可靠。

做法：sink 裡記錄 `pre = target->AsActorValueOwner()->GetActorValue(kHealth)`，接著 `AddTask` 讀 `post`，`lost = pre − post`。兩者之間同一幀的其他傷害或回復會混進來（誤差小）。一擊致死時 post ≤ 0 也照樣可以算。對 DoT 法術，這個方法只量得到命中當下那一跳。
- 近戰那條（37674 是否就是「命中 actor」那條、37673 是否在同一幀）屬於推論，探針 P8 確認。

後備：v0.4 寫的「固定扣『最大魔力 × 分擔 × 係數』」維持為探針失敗時的退路。

## 16. 「受到的法術傷害」PERK 進入點是否只作用於傷害、是否在扣血前生效

**判定：PARTIAL**。會在扣血前生效；**但不只作用於傷害**。

證據（`BGSEntryPoint::HandleEntryPoint` ID 23073 = 0x14032ECE0）：`ActiveEffect::AdjustForPerks`（ActiveEffect vtable slot 0，ID 33278，0x14053DF40）依序執行：
1. `kModSpellDuration`（0x1E，perk owner = 施法者）；
2. `kModSpellMagnitude`（0x1D，施法者）；
3. `kModIncomingSpellDuration`（0x2A，owner = **目標**，參數 = 法術、&duration）；
4. `kModIncomingSpellMagnitude`（0x29，owner = 目標，參數 = 法術、&magnitude）。

中間**沒有任何「是否敵對」的分支**，每個 ActiveEffect 都會跑。進入點條件能看到的只有「Perk Owner」和「Spell」兩個分頁，**看不到攻擊者，也看不到個別效果**。列舉值見 `include/RE/B/BGSEntryPoint.h:54-55`。
- 扣血前：AdjustForPerks 在效果套用時執行，改的是 `ActiveEffect::magnitude`，效果開始之後才扣血，所以**確實在扣血前**；DoT 的每一跳也都是縮小後的值。
- 只作用於傷害：**不成立**。友方的治療和增益、同一顆敵對法術裡的非傷害效果（減速、削抗等）都會一起被縮小，除非用 Spell 分頁的條件過濾（例如法術關鍵字 `MagicDamageFire/Frost/Shock` 或技能 = 毀滅）。外部模組的傷害法術如果沒有標準關鍵字就過濾不到。
- 物理：`kModIncomingDamage`（0x24）在 ID 42844（0x1407442F0，HitData 傷害計算）執行，早於扣血；只有武器或投射物命中會經過。

後備：v0.4 的「法術那一半改用條件式減傷效果」值得保留。更好的組合是：進入點 0x29 加上 Spell 分頁條件「法術帶毀滅類關鍵字」，覆蓋 vanilla 與多數模組的傷害法術，剩下的缺口接受。

## 17. 魔力超過上限（超載）

見 §18：引擎**不允許**當前值超過上限。做法是「把上限抬高」再加上 DLL 的「摺疊」。**判定：PARTIAL**。

---

## 18. 臨時血量／超載魔力／臨時精力：當前值能不能超過上限？

### 18.0 直接回答

**不能。在這個引擎裡，生命、魔力、耐力的「當前值」永遠不會超過「上限」。唯一的辦法是把上限抬高。**

| | 生命（血：臨時血量） | 魔力（無元素：超載） | 耐力（土：臨時精力） |
|---|---|---|---|
| 當前值可以 > 上限嗎 | **不行** | **不行** | **不行** |
| 引擎模型 | 當前 = 基礎 + 永久 + 暫時 + 傷害；上限 = 基礎 + 永久 + 暫時；傷害修正 ≤ 0 | 同左 | 同左 |
| 最乾淨的模擬 | 用「暫時」修正把上限抬高 T，DLL 每 tick 把已受的傷害先從 T 扣掉（摺疊） | 同左（摺疊時機：施法事件 + tick） | 同左（只能靠 tick，沒有耗耐力事件） |
| HUD | 條顯示滿，**不會變長**（比例 = 當前 ÷ 永久+暫時） | 同左 | 同左 |
| 自然回復 | 只回到抬高後的上限；摺疊後等於不會回填溢出 | 同左 | 同左 |
| 受傷或花費的順序 | 摺疊後**溢出先扣**（和護盾一樣） | 摺疊後**超載先花** | 摺疊後**臨時精力先花**（有 ≤1 tick 延遲） |
| 逐步衰減 | 每 tick 讓 T 減 δ，當前同步減 δ | 同左 | 同左 |
| 到期 | T 歸零，上限回原值，沒有夾值問題 | 同左 | 同左 |
| 特殊副作用 | 每次降低 T 都會觸發 `HandleHealthDamage(null, −δ)`，傷害數字類模組會顯示幻影傷害 | 從 >0 掉到 ≤0 才會中斷專注法術（我們不會觸發） | 無 |
| 讀檔、存檔 | 修正值跟著存檔；DLL 的 T 記帳要寫進 SKSE cosave | 同左 | 同左 |
| 其他模組看到的值 | `GetActorValueMax` 變大；`GetActorValuePercent` 會 **> 1.0**（分母不含暫時修正） | 同左 | 同左 |

### 18.1 證據：數值模型

- 讀取：Actor 的 ActorValueOwner vtable（0x1416560C0，ID 260543）slot 1 → 0x1406220B0（ID 37533）= `GetBaseActorValue` + (`mod[kPermanent]` + `mod[kTemporary]` + `mod[kDamage]`)（0x14063D970 把三個加總）。沒有任何夾值。
- 上限：Papyrus `GetActorValueMax` 的 native（0x14094AB00）= `GetPermanentActorValue`（vfunc 0x10）+ `mod[kTemporary]`（0x140621350，`edx=1`）。`GetPermanentActorValue` → 0x1406221E0（ID 37535）= 基礎 + `mod[kPermanent]`（Health 在 +0x228）。
- 百分比：`GetActorValuePercent`（ID 36347，0x1405D6500）= 當前 ÷ **永久值**（不含暫時），分母為 0 時回 1.0。所以抬高暫時修正時，百分比會 > 1。
- **寫入與夾值**：`ActorValueOwner::RestoreActorValue(modifier, av, value)`（`include/RE/A/ActorValueOwner.h:20`，slot 6 → 0x140621120，ID 37523）：
  - `modifier == kDamage` 時先經 vfunc 0x938 調整；新值 = 舊值 + delta。
  - 對一般 AV（AV 資訊的 flag bit 9 沒設），**新值 > 0 就改成 0**（0x140621256 → 0x140621273）；|新值| < 1e-4 也歸 0。
  - 存入後呼叫 0x1406213D0（ID 37525），它會轉到各 AV 自己的回呼（表在 0x142F39A40：Health 0x1406227A0（ID 37543）、Magicka 0x1406229F0）。
  - AV = Health 且 value < 0 時（**不論是哪一種修正**），再呼叫 `HandleHealthDamage(attacker, value)`（vfunc 0x104，0x1406212EF）。
  - Health、Magicka、Stamina 的傷害本來就是負值，所以一定走「≤ 0」這支。結論：**傷害修正不可能變成正值，當前值 ≤ 基礎 + 永久 + 暫時 = 上限**。
- `kPermanent`、`kTemporary` 沒有夾值，調高會**同時**抬高上限和當前值（傷害修正不變）。這就是強化藥水一喝下去，當前值就跟著增加的原因。
- `SetActorValue`（slot 7）改的是基礎值。`ModActorValue`（slot 5 → 0x140622F80）經過 avStorage 的通用存取器（0x14063DD60/0x14063DE00）；它對 H/M/S 實際改的是哪一層：UNCONFIRMED，**不建議使用**。CommonLib 沒有提供可以把傷害修正寫成正值的 API。
- 回復旗標與 HUD：0x140622490（ID 37539）用「永久 + 暫時」當上限：當前 < 上限時設回復旗標，≥ 上限時清掉；玩家的 HUD 比例 = 當前 ÷（永久 + 暫時）（0x1406B4710）。
- 我沒有找到任何每幀或讀檔時把當前值夾到上限的程式碼；因為夾值在寫入時就做了，也不需要。

### 18.2 證據：Fortify（Value Modifier + Recover）套用和到期時做了什麼

`ValueModifierEffect` vtable（ID 258043，0x14163DF38）：
- `ModifyActorValue`（slot 0x20，0x140567A80，ID 34286）：MGEF 有 Recover flag（`EffectSetting.h:49`）時 → `RestoreActorValue(kTemporary, av, ±mag)`；沒有 Recover、而且是生命的負值時 → 扣血函式 36345；其他情況 → `kDamage`。
- `ModifyOnFinish`（slot 0x1F，0x140567880，ID 34284），用在正強度的效果到期時：
  - **魔力、耐力**（非生命）：先把傷害修正回補 `max(0, mag − 當前)`（0x140567F10，ID 34289），再扣掉暫時修正，所以到期後 **當前 = max(當前 − mag, 0)**，不會變負。
  - **生命**：只有在「當前 ≤ mag + 1」時回補 **1 點**（0x1405678DD–0x1405678FD），然後扣掉 mag。如果當前 < mag − 1，當前會變成 ≤ 0，而且扣暫時修正時會觸發 `HandleHealthDamage(…, −mag)`。這是否會致死：UNCONFIRMED（探針 P9）。
- 所以「用 Fortify 效果、不加任何處理」的超上限模擬，行為是：**溢出最後才被花掉**（傷害打在合併的池子上），到期時不管剩多少都扣掉 mag，生命還可能被扣到 0 以下。這不是我們要的，所以需要摺疊。

### 18.3 建議做法（三種資源共用）：抬高上限 + DLL 摺疊

狀態：DLL 對每種資源記一個 `T`（我們加上去的暫時修正量），寫進 SKSE cosave（`SKSE::GetSerializationInterface()`，`include/SKSE/API.h:23`、`Interfaces.h:81`）。

- **灌入 G**（吸魔、回流、臨時血量來源）：
  - 先補滿：`need = 上限 − 當前`，`RestoreActorValue(kDamage, av, +min(G, need))`；
  - 剩下的 `over = G − need`，套上溢出上限 `cap`：`add = min(over, cap − T)`；
  - 呼叫 `RestoreActorValue(kTemporary, av, +add)`，`T += add`。上限和當前同時 +add，條保持全滿。
- **摺疊**（每次 tick；魔力再加 TESSpellCastEvent 時；生命再加 TESHitEvent 後的 task 時）：
  - `S = −GetActorValueModifier(kDamage, av)`（`Actor.h:526`，ID 37524），`k = min(S, T)`；
  - 先 `RestoreActorValue(kDamage, +k)`，再 `RestoreActorValue(kTemporary, −k)`，`T −= k`。
  - 當前值不變、上限縮小，溢出因此**先被花掉**。自然回復不會回填，因為只要 T > 0，傷害修正就一直被摺成 0。
- **衰減**：每 tick `δ = min(速率 × dt, T)`，`RestoreActorValue(kTemporary, −δ)`，`T −= δ`。已經摺疊過，當前 = 原上限 + T，所以不會跌破原上限，也就沒有死亡風險。
- **到期或關閉**：衰減到 T = 0，或一次扣掉 T。

為什麼選「直接暫時修正」而不是「Fortify 效果」：
- 效果做法每次摺疊或衰減都要 Dispel 再重施，每次都會觸發 TESMagicEffectApplyEvent 和其他模組的 `OnMagicEffectApply`（10 Hz 會很吵），而且 Dispel 和 Finish 的時序 UNCONFIRMED；
- 直接修正則安靜、精確，不產生事件。
- 代價是**殘留風險**：暫時修正會跟著存檔。在 T > 0 時拿掉 DLL，上限會永久多出 T。緩解方式：cosave 記 T，讀檔時如果功能關閉就歸還；MCM 提供「解除安裝前清除」；另外鏡像一個 GLOB，讓 Papyrus 能偵測並提示。

生命另外要注意：每次降低 T（摺疊或衰減）都會呼叫 `HandleHealthDamage(null, −k)`。有攔這個 vfunc 的模組（傷害數字、受傷音效、統計類）會把它當成受傷。魔力和耐力沒有這個呼叫。

### 18.4 使用者問的七點行為（外加耐力相關的一點）

1. **HUD**：條的比例 = 當前 ÷ 抬高後的上限，所以溢出期間**看起來是 100%，不會變長**，也沒有 >100% 的顯示（0x1406B4710 的參數，見 §18.1）。玩家需要我們自己的提示（通知或 widget）才看得到溢出量。按上限改變條長的 HUD 模組：UNCONFIRMED。
2. **自然回復**：回復旗標只看「當前 < 上限（含暫時）」。沒有摺疊時，玩家花掉的量會被回復**一路補回抬高後的上限**，等於回復在回填溢出。摺疊之後，只要 T > 0，傷害修正就是 0，不會發生。tick 之間有 ≤1 tick 的窗口可能被回復回填一點。回復作用在傷害修正上（推定，探針 P10）。
3. **受傷或花費的順序**：沒有摺疊時，溢出**最後**才花，到期時不管剩多少都扣掉。有摺疊時溢出**先**花，行為和護盾一樣。生命超出總量的一擊會直接致死，和真正的護盾相同，因為護盾量本來就包含在當前值裡。
4. **逐步衰減**：可以做到平滑遞減，方法就是每 tick 降低暫時修正（見 §18.3）。每一步當前值同步下降 δ，但永遠 ≥ 原上限。用效果的做法只能「Dispel 再重施」，是階梯狀、而且會觸發事件。
5. **到期**：摺疊加衰減下，到期時 T 已經是 0，沒有瞬間損失，也沒有閃爍。**只用 Fortify 效果**的做法，到期時魔力和耐力會 `max(當前 − mag, 0)`，生命可能跌到 ≤ 0（見 §18.2，探針 P9）。
6. **讀檔、存檔**：modifier 值跟著存檔，重新讀檔會原樣回來。DLL 的 T 要在 cosave 保存，並在 `kPostLoadGame` 核對。讀檔當下沒有夾值的問題，因為當前不可能超過上限。
7. **其他模組**：讀上限的效果（按上限百分比的傷害或回復、Ordinator 按最大耐力或魔力計算的 perk、poise 類）會看到**抬高後的上限**，效果跟著變強；條件 `GetActorValuePercent` 在溢出時 **> 1.0**，「生命 < 50%」這類門檻以永久值為分母，不受影響，但「生命 ≥ 100%」會一直成立。Wildcat、Requiem 這類會改自然回復的模組，只要是調回復率，就不衝突。
8. **（耐力）強攻和衝刺能不能用**：引擎只看當前值，衝刺時看是否 > 0（0x14060E920 的判斷），耐力越多只會撐越久。依耐力百分比判斷的 perk 條件會看到 > 1 的百分比。強攻消耗是否受上限影響：UNCONFIRMED（探針 P11）。

### 18.5 其他方案比較

- **「另一顆自有效果的強度」當第二個池**（v0.4 超載的後備）：DLL 自己記一個浮點數就是池子，不需要效果，也完全不碰 AV。缺點是**原生的法術消耗不會先花這個池**，只有我們自己的機制（滅法、法盾）能花。適合只給自家機制用的資源；不適合「花魔力時先花超載」這個需求。
- **結界（ward）吸收**：只吸收法術、只轉成魔力，不能拿來當生命池。
- **直接把傷害修正寫成正值**：屬於寫入遊戲記憶體，禁止；回復旗標與 HUD 的行為也不明。不採用。

## 19. 引擎 Hazard 放置物

**判定：PARTIAL**。

API：`TESObjectREFR::PlaceObjectAtMe(TESBoundObject*, bool)`（`include/RE/T/TESObjectREFR.h:461`，內部走 `TESDataHandler::CreateReferenceAtLocation`，`src/RE/T/TESObjectREFR.cpp:806`）；`BGSHazard` 的資料 `limit/radius/lifetime/flags/spell`（`include/RE/B/BGSHazard.h:17-31`）；`Hazard` 的執行期資料 `ownerActor/lifetime/radius/magnitude`（`include/RE/H/Hazard.h:52-63`）；`TESObjectREFR::SetActorCause/GetActorCause`（`TESObjectREFR.h:276-277`，虛擬函式）。

- 用 PlaceObjectAtMe 直接放 HAZD 時，`ownerActor` 和 `magnitude` 不會由我們設定；設定它們屬於寫入遊戲記憶體。傷害歸屬（經驗值、仇恨、友軍傷害判定）和 hazard 法術的施法者：UNCONFIRMED。`SetActorCause(player->GetActorCause())` 是可以合法呼叫的虛擬函式，能不能讓歸屬正確：UNCONFIRMED。
- 引擎原生會正確設定 owner 的路徑，是 **Explosion 的「Placed Object」欄位**（`include/RE/B/BGSExplosion.h:33` `impactPlacedObject`）：法術的投射物或爆炸在地面放置 hazard。這條路是純資料，不需要 DLL。`limit` 是每種 hazard 的同時存在上限，由引擎管理（多數量可以用多個 HAZD 表單堆出來）。
- 探針 P12：PlaceAtMe(HAZD) 和爆炸放置 HAZD 各做一次，比對傷害來源與仇恨。

後備：v0.4 的「Papyrus 每秒領域，最多 3 個」維持到 P12 通過為止。探針如果顯示爆炸放置的 hazard 歸屬正確，建議改成資料驅動（爆炸 → hazard），DLL 只負責在目標位置觸發爆炸。

---

## 20. 總表

| 能力 | 判定 | 一句話理由 |
|---|---|---|
| DLL 每秒執行點 | YES | 背景計時執行緒每 tick `AddTask` 一次；SKSE 佇列每幀在主執行緒取出（Main::Update 35565）；**task 內自我重排會在同一幀的 while 迴圈裡無窮執行，禁用** |
| 效果移除事件 | PARTIAL | `TESActiveEffectApplyRemoveEvent` 只對 formFlags bit 22（有綁 Papyrus 腳本）的 MGEF 送出；自家 MGEF 掛 stub 腳本或用 tick 輪詢 |
| 死亡事件 | YES | KillImpl 同步送 `dead=false`，36723 送 `dead=true`，要去重 |
| 死亡事件的兇手欄位 | PARTIAL | killer = 傳給 KillImpl 的 attacker（`myKiller`）；瘋狂 NPC 親手殺死時可靠，死於我們的 DoT 時算玩家 |
| 施法事件 | PARTIAL | 放出、扣魔之後才送（SpellCast 33363）；消耗用 `CalculateMagickaCost` 重算；沒有「開始唸咒」的事件 |
| 命中時讀取目標施法狀態 | YES | 唯讀 `magicCasters[i]->state/currentSpell`；state 各值的意義待探針 |
| 中斷施法 | YES | `Actor::InterruptCast(false)` = Papyrus InterruptCast 的同一條引擎路徑（55658 → 37808） |
| 效果套用事件與增益判定 | PARTIAL / YES | 套用事件在 ActiveEffect 建立前送、只有 MGEF；沖刷時直接走訪效果清單就能精確判定 |
| 多效果強度覆寫 | NO | 覆寫值一次套到全部效果；後備改成拆成單效果法術各帶覆寫值 |
| 披風關聯法術的強度覆寫 | PARTIAL | 關聯法術收到披風目前的強度，但半徑 = 強度 × 21.33，兩者綁在一起 |
| 受擊時的原生推力 API | YES | `AIProcess::KnockExplosion` = Papyrus PushActorAway 的同一條路（55682 → 38858） |
| 神佑延遲死亡的 C++ 對等 | NO | CommonLib 沒有包裝，只能寫 process 欄位或呼叫沒有包裝的位址；留在 Papyrus |
| 衝刺耐力消耗的入口 | NO | 公式只用 GMST 和裝備重量；替代：IsSprinting 條件的回復 ability，或 DLL tick 回補 |
| 引擎 Hazard 放置物 | PARTIAL | `PlaceObjectAtMe` 可用但 owner 不明；爆炸放置 hazard 是原生路徑，待探針 |
| 受擊當下讀實際扣血 | PARTIAL | TESHitEvent 比扣血早；sink 記扣血前的值、task 讀扣血後的值 |
| 受到的法術傷害 PERK 進入點 | PARTIAL | 在扣血前生效（AdjustForPerks 33278），但治療、增益與非傷害效果也一起縮小，只能用 Spell 條件過濾 |
| 魔力超過上限（超載） | PARTIAL | 當前不可能超過上限；用暫時修正抬高上限 + DLL 摺疊來模擬 |
| 臨時血量／臨時精力（新增） | PARTIAL | 同上。生命每次降低上限會觸發 `HandleHealthDamage`；耐力只能靠 tick 摺疊 |

## 21. 還需要的遊戲內探針

- **P1 執行緒**：記錄 kDataLoaded 時的主執行緒 ID；在 TESHitEvent、TESDeathEvent、TESSpellCastEvent、TESMagicEffectApplyEvent sink、tick task、Papyrus native 裡各記 `GetCurrentThreadId()`，看是否相同。
- **P2 每秒點**：計時執行緒 10 Hz + tick；開 Esc 選單、開背包、Alt+Tab、讀檔各 30 秒，確認暫停時不計時、載入時不執行、關遊戲不崩潰。
- **P3 效果移除事件**：玩家身上套兩顆同類 MGEF，一顆有 stub 腳本、一顆沒有；記錄 `TESActiveEffectApplyRemoveEvent` 各出現幾次；再確認移除事件當下 `GetActiveEffectList()` 裡還查不查得到該 uniqueID。
- **P4 兇手**：用 Frenzy 讓 NPC A 用武器殺死 B，記錄 `actorKiller`；再讓 B 死於玩家的 DoT，記錄一次。
- **P5 施法狀態**：對一名 NPC 法師，在命中 sink 和每 100 ms 記錄 `magicCasters[0..2]->state/currentSpell`，對照畫面上待機、舉手、蓄力、放出、專注各階段。
- **P6 披風**：披風 MGEF 強度 10，關聯法術強度 1（火傷），用 `CastSpellImmediate` 帶覆寫值 5 和 20 各施放一次；記錄鄰居每秒實際掉的血和影響範圍。
- **P7 推力**：對站立、坐著、騎馬、癱瘓中的 NPC 呼叫 `KnockExplosion`，看有沒有崩潰或異常。
- **P8 扣血時序**：近戰、弓、法術各打一次；在 sink 記 `GetActorValue(Health)`，AddTask 裡再記一次，確認前後差 = 實際傷害。
- **P9 Fortify 生命到期**：喝 Fortify Health +100，受傷到只剩 30，等到期：看是否死亡，並記錄到期後的生命值。
- **P10 回復與溢出**：用 `RestoreActorValue(kTemporary, Magicka, +50)` 模擬超載，花掉 30 後不摺疊，看回復是否補回抬高後的上限；再開摺疊重跑一次。
- **P11 耐力溢出**：臨時精力 +50 時：強攻、盾擊、衝刺的消耗與可用性，並記錄依耐力百分比判斷的 perk 條件結果。
- **P12 Hazard**：PlaceObjectAtMe(HAZD) 和「爆炸 → placed HAZD」各做一次：對 NPC 的傷害、仇恨是否指向玩家、同種 hazard 超過 `limit` 時的行為、hazard 法術的施法者是誰。
- **P13 死亡事件去重**：一般擊殺、擊殺動作、essential 進入流血狀態，記錄 `TESDeathEvent` 出現的次數與 `dead` 值。
