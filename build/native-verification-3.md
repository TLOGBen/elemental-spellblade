# Native 能力查證（第三輪）：N3～N6 切片會用到的引擎與程式庫能力

查證時間：2026-09-25 20:01（+08:00）。純研究：沒有改任何程式、設計文件或建置腳本。

## 0. 範圍、方法、證據來源

- 範圍：`design-latency-2026-09-20.md` §6 DLL 切片表的 N3～N6 列（含每一個「待查證」）、`元素魔戰士規劃-v0.4.md` §9 與 §10.3。以第二輪 `build/native-verification-2.md`（下稱 **v2**）為基礎：v2 已定案的項目只引用結論；v2 列為 PARTIAL 而這幾片會用到的，這裡重新查。
- 程式庫：CommonLibSSE-NG，`native/dependencies.lock.json` 鎖定 commit `b93280e832f263dbef44e44cbe2936622a02f91a`（本機 `native/deps/CommonLibSSE-NG/`）。下文的「`檔案:行`」都是這個 commit。SKSE 2.0.20 原始碼：`D:/Game/Other/SKSE/SkyrimSE/src/skse64/`。
- 執行檔：`SkyrimSE.exe` 1.5.97（sha256 見 v2 §0）；Address Library `version-1-5-97-0.bin`（用 NG 自帶的 `tests/REL/version-1-5-97-0.bin`，格式照 `include/REL/ID.h:331` `unpack_file` 解析）。
- 工具（只讀）：llvm-objdump 21.1.8（Intel 語法）＋ `build/nv3-scratch/` 裡的一次性腳本：
  - `nv3.py`：解析 Address Library、PE 區段、`.pdata` 找函式起點、E8/E9 呼叫與 RIP 相對參照搜尋、vtable 讀取、帶 ID 標註的反組譯。
  - `up.py`：由呼叫索引往上追呼叫者。
  - `api_probe.cpp` ＋ `cc.bat`：把本文**建議的每一個 CommonLib 呼叫**寫成一個不連結的翻譯單元，用專案同一套 MSVC 14.44、`/std:c++latest /permissive- /utf-8`、同樣的巨集與 include 路徑做 `cl /Zs` 語法檢查。結果 `EXIT=0`：本文寫到的型別、成員、簽名都存在、可編譯。
- 下文每條引擎行為都附 VA 與 Address Library ID；用 `python -B build/nv3-scratch/nv3.py` 裡的 `func(idva(ID))` 可以重現反組譯。
- 規則前提（專案既定）：只用事件 sink 與程式庫 API；不用 hook、trampoline、vtable patch，不寫遊戲記憶體；DLL 不存狀態、不序列化。
- 判定用語：**YES**＝靜態證據足夠，可以直接照做；**PARTIAL**＝能做，但有限制或要換做法；**NO**＝在規則內做不到；**NEEDS-IN-GAME**＝靜態分析已把範圍縮到一個問題，要玩家跑一次約一分鐘的探針才能定案。

---

## 1. 總表

| # | 能力 | 用在 | 判定 | 一句話結論 |
|---|---|---|---|---|
| 1 | 效果移除事件：送出當下查不查得到 ActiveEffect、能不能分出到期／驅散／死亡 | N3 過期終焉、退階、白熱引信、星痕引爆、死咒、浮空落地等（v0.4 §10.3 第 1 列） | **YES**（限掛了腳本的 MGEF） | 事件在 `Finish()` 之後、從清單移除之前同步送出，AE 還在清單裡、欄位都還讀得到。到期時 `elapsedSeconds ≥ duration`；驅散時 `elapsedSeconds < duration` 且目標活著；死亡時目標 `IsDead()`。旗標 `kDispelled` 三種情況都會設，**不能拿來分辨** |
| 2 | 效果套用事件 | N3 瘴氣「+劑」（暫緩項） | PARTIAL（沿用 v2） | `TESMagicEffectApplyEvent` 所有效果都送，但在 AE 建立前送出，只拿得到 MGEF |
| 3 | 讀目標的效果清單與強度 | N3 目標側倍率、中毒讀取—疊加、N4 自有資源池 | **YES**（只能在主執行緒） | `AsMagicTarget()->GetActiveEffectList()` 直接走訪；引擎本身對這張清單**沒有鎖**。強度讀 `ae->magnitude`；`GetMagnitude()` 會套 taper |
| 4 | 同一顆法術重套時舊的效果怎麼處理 | N3 刷新版印記、階梯重套、中毒重套、N4 資源池重套 | **PARTIAL → NEEDS-IN-GAME** | 同一施法者重套同一顆法術時，引擎會 `Dispel(true)` 舊的，**但 Value Modifier、Dual Value Modifier、Accumulate Magnitude、Paralysis 等原型會跳過這一步**。一律改成 DLL 自己先 `Dispel(true)` 舊的再施放，不靠引擎 |
| 5 | `ActiveEffect::Dispel` 的時序 | N3「切掉」、沖刷 | **YES** | `Dispel(true)` 當場 `Finish()` 並送移除事件；`Dispel(false)` 對一般法術只設旗標，要等下一次效果更新才結束 |
| 6 | 施法事件（反咒） | N4 反咒 | PARTIAL（沿用 v2） | 只有「放出、扣完魔力之後」這個時點；消耗用 `CalculateMagickaCost` 重算 |
| 7 | 命中時讀目標是否正在詠唱 | N4 雷滿格法術麻痺、斷咒 | **YES** | `magicCasters[i]->state` 的狀態機已經從反組譯解出來：1 請求、2 蓄力、3 蓄滿、4 放出、5／6 施放中（專注法術停在 6）、7／8 失敗、9 中斷。NG 列舉的標籤有一部分是錯的 |
| 8 | 中斷施法 | N4 | YES（沿用 v2） | `Actor::InterruptCast(false)` 就是 Papyrus `InterruptCast` 同一條引擎路徑 |
| 9 | `TESDeathEvent` 的時機與兇手 | N5 化灰、亡者歸來、毒的死亡擴散、連殺、狂宴 | **YES** | `dead=false` 那一次在 `KillImpl` 裡同步送出，**這時目標身上的效果全部還在**；死亡驅散要到下一次效果更新才發生。兇手讀 `myKiller`，送事件前就寫好了 |
| 10 | 用 process lists 掃附近的 actor | N5 融斷掃描、範圍終焉、「附近 1 人」擴散 | **YES**（只能在主執行緒） | `ProcessLists::highActorHandles` 逐一 `handle.get()`；先收集 handle 再動手 |
| 11 | 背景計時執行緒每 tick 丟一個主執行緒 task | N5 放血、N6 每秒計時、N4 超載衰減 | YES（沿用 v2） | SKSE `AddTask` 有 critical section，可以從別的執行緒呼叫；**不需要任何 hook**。設計表 N6 列「一個每幀或計時 hook」的說法要改 |
| 12 | 熱鍵輸入 sink | N6 | **YES** | `BSInputDeviceManager` 在 `Main::Update` 裡同步派送輸入事件（主執行緒，同一幀比 SKSE task 早） |
| 13 | 放置 Hazard（領域） | N6 領域改引擎 Hazard（v0.4 §10.3 第 4 列） | **PARTIAL → NEEDS-IN-GAME**（改走新路徑） | 查到一條比 v2 好的原生路徑：**Spawn Hazard 原型的 MGEF 用 `CastSpellImmediate` 施放**，引擎自己設好 owner＝施法者、magnitude＝效果強度、lifetime、數量上限，只打對 owner 有敵意的人。`PlaceObjectAtMe(HAZD)` 雖然能用 `SetActorCause` 設 owner，但 lifetime 是 −1（永不消失）、不受上限管，不建議 |
| 14 | 沖刷「施法得來、有持續時間、屬增益」並排除種族能力、任務腳本、天賦、疾病、本模組效果 | N3 浸濕滿層沖刷 | **YES** | 關鍵新證據：Papyrus `Spell.Cast` 走 `GetMagicCaster(kInstant)`，所以**任務腳本施放的效果 `castingSource == kInstant`**；真正「用手施法」的是 `kLeftHand`／`kRightHand`。加上法術類型與 MGEF 旗標，可以精確排除 |
| 15 | 各事件在哪個執行緒送出（共通） | 全部 | **NEEDS-IN-GAME**（強烈傾向主執行緒） | 近戰命中經由 `BSTaskPool` 的「平行階段就排隊、否則當場執行」包裝；輸入事件確定在主執行緒。一行 log 就能定案（探針 X1） |

**會逼出設計修改的，只有這幾條**（細節見 §17）：第 4 條（重套一律先驅散舊的）、第 13 條（領域改用 Spawn Hazard 原型，不用 PlaceAtMe）、第 11 條（N6 不需要 hook，崩潰面描述要改）、第 1 條（移除事件只給「要結算的」低頻效果掛 stub 腳本）。

---

## 2. 效果移除事件：送出當下的狀態，以及能不能分出到期／驅散／死亡

**判定：YES**（前提和 v2 §3 一樣：只有掛了 Papyrus 腳本、也就是 formFlags bit 22 有設的 MGEF 才會送）。

API：`RE::TESActiveEffectApplyRemoveEvent { caster, target, activeEffectUniqueID, isApplied }`（`include/RE/T/TESActiveEffectApplyRemoveEvent.h:13-16`）；`ActiveEffect` 的欄位 `elapsedSeconds`／`duration`／`magnitude`／`flags`／`usUniqueID`／`castingSource`（`include/RE/A/ActiveEffect.h:108-115`）。

證據：
- 效果的每幀更新是 `ActiveEffect` 更新函式 ID 33317（0x14053FB60），由 `MagicTarget` 的效果更新迴圈 ID 33743（0x1405539D0）逐一呼叫。
- **到期**：0x14053FE4A–0x14053FE62 在 `elapsed + dt > duration` 時把 `elapsedSeconds` **夾成剛好等於 `duration`**；0x14053FF04–0x14053FF36 在 `duration ≤ elapsed` 時設 `flags |= 0x40000`（bit 18 `kDispelled`）。所以**到期也會設 kDispelled**，這個旗標不能用來分辨。
- **驅散**：`ActiveEffect::Dispel` ID 33286（0x14053E380）先設 bit 18，再依 `force` 決定當場或下一幀結束（§6）。此時 `elapsedSeconds < duration`。
- **死亡**：0x14053FF0F–0x14053FF36：目標 `IsDead(true)`（vfunc 0x4C8＝`TESObjectREFR::IsDead`，`include/RE/T/TESObjectREFR.h:353` 的 slot 0x99）而且 `ShouldDispelOnDeath()`（vfunc 0x80）時設 bit 18。`ShouldDispelOnDeath` 的實作是 ID 33309（0x14053F8C0）＝`!(MGEF.flags & kNoDeathDispel)`。**注意**：NG `ActiveEffect.h:78` 的註解寫成 `flags.any(kNoDeathDispel)`，方向寫反了，以反組譯為準。
- **結束與送事件的順序**：0x14053FF7A 起：`CanFinish()`（vfunc 0xB0）→ `Finish()`（vfunc 0xA8，Value Modifier 在這裡把 AV 還回去）→ 設 bit 17（0x20000，「已結束」）→ 清掉 hit effect（ID 33275）→ 只要 `usUniqueID != 0` 就經 ID 33346 送 `isApplied=0`（0x140540069）。
- **從清單移除在事件之後**：33743 在 33317 回來以後才看 bit 18，設 bit 31（0x80000000，「待移除」），再呼叫 ID 33764（0x140554C80）把它從清單拿掉（0x140553AAB–0x140553BE3）。所以**事件送出時，AE 還在目標的 `GetActiveEffectList()` 裡**，`magnitude`、`elapsedSeconds`、`duration`、`spell`、`caster` 都還是原值。

建議做法（sink 內只讀、記帳，寫入丟 `AddTask`）：
```
移除事件：用 activeEffectUniqueID 在 target 的清單找到 ae
  到期：ae->duration > 0 && ae->elapsedSeconds >= ae->duration
  死亡：否則，target->IsDead()
  驅散：其他（包含別人的驅散、我們自己的「切掉」、同一顆法術被重套時的舊實例）
```
- 我們自己在命中裡「切掉」或「重套」造成的移除，靠設計已經寫的重入旗標過濾（事件會在我們的 `Dispel(true)` 呼叫**裡面**同步送回來，§6）。
- 同一幀剛好到期又剛好死亡，會判成「到期」，可接受。

崩潰面：移除事件可能在目標自己的效果更新迴圈裡送出（到期、死亡驅散都是）。這時如果在 sink 裡對同一個目標 `CastSpellImmediate` 或 `Dispel`，等於在引擎走訪清單時改它。**sink 裡一律只讀，動作丟 `AddTask`**。

代價（新發現，影響 stub 腳本的使用範圍）：掛了腳本的 MGEF，每次套用時 Papyrus VM 也是這個事件的 sink，會為這個 AE 建一個 ActiveMagicEffect 物件並嘗試派送 `OnEffectStart`／`OnEffectFinish`（沒有處理函式就不執行任何程式碼）。每擊都會重套的效果（階梯、中毒）不建議掛；只給「到期要結算」的低頻效果（印記、白熱引信、星痕、死咒、浮空）掛，其餘用 tick 輪詢。

尚未確認：讀檔、換場景卸載 actor 時會不會對仍在的效果送移除事件。靜態看不出來，列入探針 N3-1。

## 3. 效果套用事件

**判定：PARTIAL**（沿用 v2 §9，沒有新變化）。`TESMagicEffectApplyEvent` 由 ID 33742（0x140553750）在 0x14055388B 送出，這時 AE 還沒建立（建立在同一函式稍後的 ID 33763，0x140553938）。只拿得到 `magicEffect`（FormID）、caster、target。暫緩項「瘴氣每跳 +劑」若採方案 (a)，DLL 在這個事件裡只能記下「某目標被某 MGEF 套了一次」，要把劑量併進中毒，得等下一個 task 去讀清單。

## 4. 讀目標的效果清單與強度

**判定：YES**，只能在主執行緒。

API：`actor->AsMagicTarget()->GetActiveEffectList()`（`include/RE/A/Actor.h:720`、`include/RE/M/MagicTarget.h:84`，回傳 `BSSimpleList<ActiveEffect*>*`，可能是 null）；或 `MagicTarget::VisitEffects`（`MagicTarget.h:96`，ID 33756）。`ActiveEffect::GetBaseObject()`、`GetCasterActor()`（`ActiveEffect.h:91-93`）。

證據：
- `VisitEffects`（0x140554500）就是單純走訪 `GetActiveEffectList()`，**沒有任何鎖**；引擎自己的更新迴圈 33743 也沒有鎖。所以只能在修改清單的同一條執行緒（主執行緒）讀。
- `GetMagnitude()` ID 33282（0x14053E120）：AE 有 bit 9（`kRecovers`）時直接回傳 `magnitude`；沒有的話，用 MGEF 的 taper 參數和剩餘時間經 ID 25929 算出衰減後的值。所以**讀「層數／劑量」一律讀 `ae->magnitude`**（我們自己的 MGEF 不設 taper 時兩者相同），要剩餘時間就讀 `duration − elapsedSeconds`。

建議用法：
- 找自家效果：比對 `ae->GetBaseObject()` 指標是否等於 manifest 載入時解析好的 `EffectSetting*`；跳過 `flags & kDispelled` 的（已經在結束的）。
- 目標側倍率（N3）：命中 sink 裡直接讀（前提是 sink 在主執行緒，§16 探針 X1）。
- 自有資源池（N4 超載、護血、蓄勁；v0.4 寫「值存在自有 MGEF 的強度裡」）：讀 `ae->magnitude`。

崩潰面：清單節點在效果移除時被釋放；**不要跨 task 保留 `ActiveEffect*`**，要保留就存 `usUniqueID` 或 MGEF 指標，下次重新找。

## 5. 同一顆法術重套時，舊的效果會怎樣（新增項，N3／N4 都靠它）

**判定：PARTIAL**；Value Modifier 類要 **NEEDS-IN-GAME**。建議做法本身不依賴探針結果。

證據（`MagicTarget` 加效果的核心 ID 33763，0x140554700）：
- 0x140554982–0x1405549A6：用 MGEF 原型（`EffectSetting+0xC0`）查原型表 ID 500623（0x141DB0020，每筆 24 位元組，旗標在 +8），取旗標 bit 4。
- bit 4 **沒設**時，0x140554A5F 呼叫 ID 33720，用 visitor ID 33765（0x140554DF0）走訪目標清單：**同一顆法術、同一個施法者 handle**、同一個 source、同一個 castingSource（或任意）、還沒被驅散的舊 AE → 目標不在自己的更新迴圈裡就 `Dispel(true)`（0x140554EA1），在迴圈裡就排進 `postUpdateDispelList`（ID 33766）。這發生在新 AE 建立**之前**。
- 原型表的 bit 4（從執行檔直接讀出）：**有設、也就是「不會自動驅散舊的」**：Value Modifier(0)、Dual Value Modifier(5)、Bound Weapon(17)、Summon Creature(18)、Paralysis(21)、Value and Parts(31)、Accumulate Magnitude(32)、Grab Actor(45)。其餘（Script(1)、Absorb、Calm、Frenzy、Invisibility、Peak Value Modifier(34)、Cloak(35)、Spawn Hazard(40)、Stagger…）都會自動驅散舊的。
- Value Modifier 類的舊實例在其他地方是否被取代，靜態追不完（另有 ID 33443、33776 兩個也會呼叫 33720 的 visitor，觸發條件未解）。

結論與建議：
- **N3 的刷新／升階／中毒重套、N4 的資源池重套，一律由 DLL 自己先找到舊 AE、讀完 `magnitude`、`Dispel(true)`，再 `CastSpellImmediate`**（同一個 task 裡）。這樣不管引擎對該原型會不會自動取代，結果都一樣是「只剩一個」。
- 自有資源池、印記、階梯這類「只存數字」的 MGEF，建議用 **Script 原型**（引擎也會自動取代，雙重保險；沒有 AV 副作用）。中毒 DoT 必須是 Value Modifier（要扣血），所以一定要靠 DLL 先驅散。
- `CastSpellImmediate` 只能覆寫強度，**不能覆寫持續時間**（v2 §10 的套用 visitor 只寫 magnitude）。重套等於把時間重新計滿；如果設計要「保留剩餘時間」，做不到，只能接受「重套＝刷新時間」。

## 6. `ActiveEffect::Dispel(bool force)` 的時序

**判定：YES**。

API：`ActiveEffect::Dispel(bool a_force)`（`include/RE/A/ActiveEffect.h:90`，`src/RE/A/ActiveEffect.cpp:8`，ID 33286）。

證據（0x14053E380）：已經是 kDispelled 就直接 return；否則設 bit 18。`force == true` → 立刻跳到 33317（dt = 0），當場 `Finish()` 並送移除事件。`force == false` → 如果 ID 514178 單例 +0x160 為 0，而且 ID 33289（0x14053E670）回傳 true，就**只設旗標、不結束**；33289 對一般法術（類型不是疾病、能力、成癮）只要 bit 31 沒設就回傳 true。也就是：`Dispel(false)` 對一般法術是「下一次這個目標的效果更新才結束」（通常 ≤ 1 幀）。

建議：N3「切掉舊印記、套新印記」與沖刷一律用 `Dispel(true)`，順序才確定；先收集要驅散的指標，再逐一驅散（和 NG `MagicTarget::DispelEffectsWithArchetype` 的寫法一樣，`src/RE/M/MagicTarget.cpp:17-35`）。`Dispel(true)` 不會把節點從清單拿掉（拿掉是更新迴圈做的），所以邊收集邊驅散也不會讓走訪斷掉，但先收集比較好讀。

## 7. 施法事件（反咒）

**判定：PARTIAL**（沿用 v2 §6）。`TESSpellCastEvent` 在 `ActorMagicCaster::SpellCast`（ID 33363）扣完魔力之後才送出，沒有「開始唸咒」的時點。N4 反咒的定義（「施法者帶破魔印時觸發，讀該次施法消耗的魔力算真傷」）正好是放出後的時點，用 `spell->CalculateMagickaCost(caster)`（`include/RE/M/MagicItem.h:111`）重算消耗即可；雙持倍率與專注法術只算開始那一次，限制照 v2。

## 8. 命中時讀目標是否正在詠唱（雷滿格法術麻痺、斷咒）

**判定：YES**。v2 §7 留下的「state 各值的意義待探針」，這一輪從狀態機的反組譯解出來了。

API：`actor->GetActorRuntimeData().magicCasters[4]`（`include/RE/A/Actor.h:679`，可能是 null）；`MagicCaster::state`、`currentSpell`、`castingTimer`（`include/RE/M/MagicCaster.h:89-91`）；`MagicItem::GetCastingType()`（`MagicItem.h:82`）。

狀態機（寫入 `MagicCaster+0x30` 的位置）：

| 值 | 意義 | 寫入點 |
|---|---|---|
| 0 | 閒置／收手 | FinishCast ID 33657（0x14054F6DE）、ID 33627、33631、33644 |
| 1 | 請求施法（舉手） | ID 33623（0x14054C459），接著呼叫 `RequestCastImpl` |
| 2 | 蓄力中（`castingTimer` 倒數） | ID 33663（0x14054F9BC）＋`StartChargeImpl`；`UpdateImpl` ID 33622 在 state 2 時倒數 |
| 3 | 蓄滿、舉著等放 | `UpdateImpl` 0x14054C2BF 倒數到 0 時；ID 33664（0x14054F9FC）＋`StartReadyImpl` |
| 4 | 放出（開始施放） | ID 33665（0x14054FA36）＋`StartCastImpl` |
| 5 | 施放檢查中 | ID 33629（0x14054C9B9），接著 CheckCast 與 FindTargets |
| 6 | 施放中；專注法術會一直停在 6 | FindTargets ID 33632（0x14054CDF9）；`UpdateImpl` 在 6 時累加 `castingTimer`、處理專注的扣魔與中斷 |
| 7、8 | 請求失敗 | ID 33623（0x14054C3AF、0x14054C42F） |
| 9 | 被中斷 | `MagicCaster::InterruptCast` ID 33630（0x14054CBB6）、ID 33649 |

NG 的列舉（`MagicCaster.h:29-40`）把 5 標成 `kCharging`、6 標成 `kCasting`，**5 的標籤不對**（真正的蓄力是 2）；3 `kReady` 正確。

建議判定「正在詠唱」：
```
任一 magicCasters[i] 非 null、currentSpell 非 null，且
  state ∈ {1, 2, 3, 4}，或
  state == 6 且 currentSpell->GetCastingType() == kConcentration
```
射出後的「射後不理」法術在 5／6 只停留一瞬間就回 0，不算詠唱。雷 30% 機率在 C++ 擲骰；中斷用 §9。建議保留探針 N4-2（一分鐘）確認畫面上的「舉手／蓄力／放出」對上表格。

## 9. 中斷施法

**判定：YES**（沿用 v2 §8）。`Actor::InterruptCast(false)`（`include/RE/A/Actor.h:577`，ID 37808）＝Papyrus `ObjectReference.InterruptCast` 同一條路（ID 55658 → 37808）。放在 `AddTask` 裡呼叫，先檢查 `Is3DLoaded()`、`!IsDead()`。

## 10. `TESDeathEvent` 的時機：在死亡驅散之前還是之後、兇手拿不拿得到

**判定：YES**。

API：`RE::TESDeathEvent { actorDying, actorKiller, dead }`（`include/RE/T/TESDeathEvent.h:13-15`）；`Actor::GetActorRuntimeData().myKiller`（`Actor.h:654`）。

證據：
- `KillImpl` ID 36872（0x140603B30）在 0x1406045A5 先把 attacker 寫進 `myKiller`，0x14060499F 同步送 `dead=false`（v2 §4）。
- **死亡驅散不在 `KillImpl` 裡**：死亡時的效果清除是 §2 那段 0x14053FF0F 的判斷——每個效果在**自己下一次更新**時看到目標 `IsDead(true)` 而且沒有 `kNoDeathDispel`，才被驅散。`KillImpl` 整個函式（0x140603B30–0x140605596）的 202 個有 ID 的直接呼叫裡，沒有任何一個落在 33000–34199（魔法效果）區段；間接的 vfunc 呼叫無法逐一排除，由探針 N5-1 確認。
- 所以 **`dead=false` 那一次事件送出時，目標身上的印記、階梯、中毒全部還在**，可以在 sink 裡讀清單判定化灰、亡者歸來、詛咒層數、中毒劑量。即使兇手是目標自己身上的 DoT（這時 `KillImpl` 是從目標的效果更新迴圈裡呼叫），事件當下其他效果也都還沒被驅散。
- `dead=true` 那一次（ID 36723 → 37436）比較晚，效果可能已經清掉；**讀印記一律用 `dead=false` 那次**，兩次都到時依 `dead` 去重。
- 死亡驅散後，掛了腳本的效果會各送一次移除事件，而且 `target->IsDead()` 為 true，正好對上 §2 的「死亡」分類。

建議：sink 裡讀 `actorDying` 的效果清單與 `myKiller`、記下要做的事；範圍掃描、施放、推力全部丟 `AddTask`（sink 可能正在目標自己的效果迴圈裡）。狂宴的判定維持 v2 §5 的折衷（killer 非 null、不是玩家、身上有我們的瘋狂 MGEF）。

尚未確認：`KillImpl` 以外那 8 個呼叫 36723 的路徑（例如腳本 `Kill`、讀檔時已死亡）是否可能只送 `dead=true`。探針 N5-1。

## 11. 用 process lists 掃附近的 actor

**判定：YES**，只能在主執行緒。

API：`RE::ProcessLists::GetSingleton()`、`highActorHandles`（`include/RE/P/ProcessLists.h:36、69`）、`ForEachHighActor`（`:40`，實作 `src/RE/P/ProcessLists.cpp:38-46` 只是走訪 handle 陣列、`handle.get()`）；距離 `GetPosition().GetDistance()`；過濾 `Is3DLoaded()`、`IsDead()`、`IsHostileToActor(player)`（`Actor.h:593`）、`IsPlayerTeammate()`（`:603`）、`IsCommandedActor()`（`:586`）。另有 `TES::ForEachReferenceInRange`（`include/RE/T/TES.h:70`），會掃到所有參照，比較貴，不建議。

證據與注意事項：
- `highActorHandles` 是 `BSTArray<ActorHandle>`，NG 走訪時沒有鎖（`ProcessLists.cpp:38-46`），只有特效清單有 spinlock（`ProcessLists.h:76-80`）。陣列由主執行緒的 process 更新改動，所以**只能在 `AddTask` 或主執行緒的 sink 裡掃**。
- `handle.get()` 回傳 `NiPointer`（有參考計數），單次 task 內安全。
- 玩家不在這個陣列裡。高處理層只涵蓋載入範圍內、正在活動的 actor（通常是戰鬥半徑內），對「附近 15 公尺」足夠；遠處的中、低處理層 actor 不在內，這正好符合設計。
- 單位：1 公尺 ≈ 70 遊戲單位（1 單位 ≈ 1.43 公分）。

建議：先收集符合條件的 `ActorHandle` 進 `std::vector`，走訪結束後再逐一施放；施放造成的死亡會同步觸發我們自己的死亡 sink（重入），所以死亡 sink 不能假設「不在掃描中」。

崩潰面：從非主執行緒走訪；走訪途中改陣列（一邊走一邊施放可能讓 actor 被移出高處理層）。先收集再動手就能避開。

## 12. 背景計時執行緒，每 tick 丟一個主執行緒 task

**判定：YES**（沿用 v2 §2，這一輪補了執行緒安全的原始碼證據）。

- SKSE 2.0.20 `skse64/Hooks_Threads.cpp`：`TaskInterface::AddTask` 用 `s_taskQueueLock`（ICriticalSection）保護 `s_tasks`，所以**可以從我們自己的執行緒呼叫**。取出端在 `Main::Update`（ID 35565）+0x6B8 的主執行緒呼叫點。
- 已寫進 `api_probe.cpp` 的樣板：`std::thread` 每 100 ms 醒來，用 atomic 旗標保證「上一個 tick 還沒執行就不再排」，task 裡先看 `UI::GetSingleton()->GameIsPaused()`（`include/RE/U/UI.h:83`）。**task 不能自己重排自己**（v2 §2：SKSE 的取出迴圈會在同一幀無限執行）。
- 每 tick 的經過時間用 steady_clock 差值自己算，不要假設剛好 1 秒。

對設計文件的影響：`design-latency-2026-09-20.md` §6 N6 列寫的「若做：一個每幀或計時 hook，是全案最大的崩潰面」已經不成立——不需要 hook，崩潰面只有「主執行緒上一個一般 task」，和 N1 的命中 sink 同一級。v0.4 §9 N6 的描述沒有這個錯誤。

## 13. 熱鍵輸入 sink

**判定：YES**。

API：`RE::BSInputDeviceManager::GetSingleton()->AddEventSink(BSTEventSink<InputEvent*>*)`（`include/RE/B/BSInputDeviceManager.h:21-45`，繼承 `BSTEventSource<InputEvent*>`；`BSTEvent.h:59`）；`ButtonEvent::IsDown()`／`IsUp()`／`HeldDuration()`（`include/RE/B/ButtonEvent.h:18-24`）；`IDEvent::GetIDCode()`（`include/RE/I/IDEvent.h:19`）；`InputEvent::GetDevice()`、`next`。過濾：`UI::GameIsPaused()`、`UI::IsMenuOpen(Console::MENU_NAME)`（`UI.h:91`）、`ControlMap::textEntryCount`（`include/RE/C/ControlMap.h:110`）、`IsMovementControlsEnabled()`（`:95`）。

證據：`Main::Update`（0x1405B2FF0）在 0x1405B33B0 呼叫 `BSInputDeviceManager::PollInputDevices` ID 67315（0x140C150B0，`this` 由 ID 516574＝NG `Offset::BSInputDeviceManager::Singleton` 載入），它在 0x140C1512B 呼叫 ID 67355（0x140C15E00），也就是 `BSTEventSource<InputEvent*>::SendEvent`（在 +0x48 取 spinlock、逐一呼叫 sink 的 vfunc 1）。所以**輸入事件在主執行緒同步派送**，而且在同一幀的 SKSE task（0x1405B36A8）之前。

建議：sink 裡只做「按下時把切換請求記進 atomic 或直接 `AddTask`」；因為已在主執行緒，直接做也可以。回 `kContinue`，不吃掉別人的輸入。設計說熱鍵「可留 `ESSBInput`，DLL 版列為選配」，兩者都可行；DLL 版少一趟 Papyrus。

## 14. 放置 Hazard（領域）

**判定：PARTIAL → NEEDS-IN-GAME**。v2 §19 的兩條路之外，這一輪找到第三條、也是最乾淨的一條。

### 14.1 引擎建立 hazard 的共同入口

`CreateHazard` ID 42786（0x140740810）接一份建立資料（+0x00 BGSHazard、+0x08 cell、+0x10 位置、+0x38 `ActorCause*`、+0x40 lifetime、+0x44 radius、+0x48 magnitude）：
- 0x1407408B4 呼叫 ID 42780 做**同種 hazard 數量上限**（`BGSHazardData::limit`，`include/RE/B/BGSHazard.h:25`）的處理；
- 建構子 ID 42784（0x140740660）：`ownerActor = ActorCause 的 actor handle`（0x140740730），lifetime 預設取 HAZD 的 `data.lifetime`（0x140740757）；
- 0x140740A42–0x140740A82 用建立資料覆寫 lifetime、radius、**magnitude**。
- 資料填寫 ID 42774（0x14073FE00）：HAZD 有「Inherit Duration」就用法術的持續時間、有「Inherit Radius」就用法術的範圍；MGEF 有 Power Affects Duration／Magnitude 時再乘上 power。

呼叫 42786 的有：**`SpawnHazardEffect`**（0x1405C197B）、投射物／爆炸撞擊（ID 43022，0x1407539A8，owner 取投射物的 `GetActorCause()`，vfunc 0x288）、另外兩處（ID 13631 與一處沒有 ID 的區塊）。

### 14.2 hazard 怎麼傷人（歸屬、仇恨、友軍）

`Hazard` 套用 visitor ID 42814（0x140741D30），對半徑內每個 actor：
- **跳過 owner 自己**（0x140741DB7）；
- owner 存在時，只打 `Actor::GetHostileToActor`（ID 36537＝NG `Offset::Actor::GetHostileToActor`，`include/RE/Offsets.h:13`）為真的目標（0x140741DC5）——**只打對 owner 有敵意的人**，不會誤傷中立 NPC 或隊友；
- 已經有這個 hazard 法術效果的跳過（ID 33729）；
- 施法者＝**owner 的 instant 施法器**（`GetMagicCaster(3)`，0x140741E54）；沒有 owner 時用一個臨時的非 actor 施法器；
- `CastSpellImmediate(hazard 法術, …, magnitudeOverride = hazard.magnitude)`（0x140741E68、0x140741E92）。所以**傷害歸屬、經驗、仇恨都算 owner 的**；magnitude 為 0 時等於不覆寫。

### 14.3 三條放置路徑比較

| 路徑 | owner | magnitude | lifetime | 數量上限 | 結論 |
|---|---|---|---|---|---|
| **A. Spawn Hazard 原型 MGEF，DLL 用 `CastSpellImmediate` 施放** | `SpawnHazardEffect` 建構時取施法者的 `GetActorCause()`，沒有就建一個（0x1405C1597–0x1405C1617） | ＝這個效果的 `GetMagnitude()`（0x1405C192B），也就是**我們的 magnitudeOverride** | HAZD lifetime，或 Inherit Duration 時＝法術持續時間 | 有（走 42786 → 42780） | **建議**。純資料＋既有的 `CastSpellImmediate`，沒有新 API |
| B. 爆炸／投射物的 Placed Object | 投射物的 ActorCause（施法者） | 依 power 縮放 | 同上 | 有 | 可用，但要在目標位置生出爆炸，DLL 不好控制強度 |
| C. `PlaceObjectAtMe(HAZD)` | 預設沒有；可以呼叫 `Hazard::SetActorCause`（虛擬函式 0x50，ID 42798，只是 `ownerActor = *cause`）設定 | **0**，沒有合法的設定方法 | `InitItemImpl` ID 42792 設成 **−1.0**（0x140740E19）；更新 ID 42791 只在 lifetime > 0 時才會到期（0x140740D4D–0x140740D69）→ **永不消失** | 不走 42780 | **不建議**：要 DLL 自己記得去刪，違反「DLL 不存狀態」 |

路徑 A 的細節：
- `SpawnHazardEffect::Start` ID 35910（0x1405C19E0）→ ID 35909（0x1405C1840）在**效果目標的位置**建立 hazard；`Finish` ID 35906（0x1405C16F0）：效果**被提早驅散**（`elapsed < duration`）時連 hazard 一起移除（ID 42787），正常到期則讓 hazard 自己活到 lifetime。
- 所以做法是：一顆 Spawn Hazard 原型的 MGEF（associated item＝HAZD），DLL 在要開領域時 `CastSpellImmediate(spell, false, 目標 actor, 1.0, false, magnitudeOverride = 領域每跳強度, player)`。`limit` 由引擎管；同時多個領域就是多個 HAZD 表單（或把 limit 設大）。
- 要注意：hazard 的位置是效果目標（一個 actor）的位置；想放在「地上某一點」而不是某個 actor 腳下，要用 Target Location 傳遞方式的法術，那就需要投射物，DLL 的即時施放不適用。

崩潰面：路徑 A 沒有新的崩潰面（和 N1 起就在用的 `CastSpellImmediate` 一樣）。未確認的只剩行為：owner 是否確實是玩家（經驗與仇恨）、hazard 法術拿到的強度是否等於我們的覆寫值、`limit` 滿了時是擠掉最舊的還是不放。探針 N6-3。

## 15. 沖刷：「施法得來、有持續時間、屬增益」，排除種族能力、任務腳本、天賦、疾病、本模組效果

**判定：YES**。

證據（新增的關鍵一條）：Papyrus `Spell.Cast` 的 native（ID 55149，0x140980930，在 ID 55152 以字串 `"Cast"` 註冊）排一個 VM task，task 的執行者 ID 55168（0x1409817C0）在 0x140981834 用 **`GetMagicCaster(3)`＝kInstant**，再呼叫 vtable slot 1（`CastSpellImmediate`，0x1409818CB）。`AddTargetData.castingSource`（`include/RE/M/MagicTarget.h:67`）來自施法器的 `GetCastingSource()`，存進 `ActiveEffect::castingSource`（`ActiveEffect.h:115`）。所以：
- 任務腳本 `Spell.Cast`、`DoCombatSpellApply`、我們自己的 `CastSpellImmediate`（N1 起用 instant 施法器）、披風關聯法術（v2 §11：castingSource 3）→ `kInstant`（3）；
- 能力、天賦加的能力 → 法術類型 `kAbility`；
- 種族力量、次要力量、龍吼 → `kPower`／`kLesserPower`／`kVoicePower`，施法來源 `kOther`（2）；
- 疾病 → `kDisease`；藥水、毒藥 → `kPotion`／`kPoison`；附魔 → `kEnchantment`；
- NPC 或盟友真正「用手施法」（含卷軸、法杖）→ `kLeftHand`／`kRightHand`。

判定式（寫在 `api_probe.cpp` 的 `DispelBuffs`，已通過編譯）：
```
spellType ∈ { kSpell, kScroll, kStaffEnchantment }         // 施法得來（排除能力、力量、龍吼、疾病、藥水、附魔）
castingSource ∈ { kLeftHand, kRightHand }                   // 排除任務腳本、DoCombatSpellApply、我們自己、披風
duration > 0 && elapsedSeconds < duration                   // 有持續時間、還沒到期
!base->IsHostile() && !base->IsDetrimental()                // 屬增益（EffectSetting.h:143-144）
!(flags & kDispelled)                                       // 還沒在結束
spell->GetFile(0) != 我們的 ESP                              // 排除本模組的印記、階梯（或比對 manifest 的 MGEF 清單）
archetype ∉ { kSummonCreature, kBoundWeapon, kReanimate, kCommandSummoned }   // 建議：召喚與綁定武器不算「增益」，由設計決定
```
先收集再 `Dispel(true)`（§6），放在 `AddTask` 裡。「是不是重新疊滿」這件事由 N3 的命中邏輯判斷（讀浸濕 AE 的 `magnitude` 由未滿變滿），與本判定無關。

限制：別的模組如果用自己的 DLL 從手部施法器施放「任務用」的增益，會被當成一般增益沖掉；機率很低，接受。

## 16. 各事件在哪個執行緒送出（所有 sink 共通）

**判定：NEEDS-IN-GAME**，但靜態證據強烈指向主執行緒。

- 輸入事件：確定在主執行緒（§13）。
- 近戰命中：命中處理 ID 37650（0x140627930，會送 TESHitEvent，v2 §15）只由 `BSTaskPool` 的執行函式 ID 36016（0x1405C6EE0，0x1405C7707）呼叫；包裝函式 ID 35917（0x1405C1D70）等一整排是「全域旗標 ID 509007（0x141DEF8A0）有設時排進 task 佇列、否則當場執行」。旗標由 ID 13646（0x14016EA00，0x14016EAD6 清除）在主迴圈管理；佇列由 `BSTaskPool::ProcessTaskQueue` ID 35916 在 `Main::Update` 取出（v2 §2）。也就是引擎刻意把命中結算導回主執行緒，平行階段時延後、非平行階段時由呼叫者（主迴圈）當場做。
- 死亡、效果移除：由效果更新迴圈或傷害處理呼叫，與命中同一條路徑，推定也在主執行緒。
- N1 的命中 sink 已經在 sink 裡直接呼叫 `CastSpellImmediate`，2026-09-23 探針卡全部通過，也符合這個推定。

建議：N3 的第一個建置在每個 sink 的第一次觸發時 log 一次 `GetCurrentThreadId()`，與 `kDataLoaded` 時記下的主執行緒 ID 比對（探針 X1，不需要玩家額外操作）。在確認之前，sink 內「讀」可以照做，「寫」一律 `AddTask`——這條規則本來就是本文所有建議的前提。

---

## 17. 會逼出設計修改的地方

1. **重套一律先驅散舊的（§5）**。`design-latency` §6 N3 列「中毒讀取—疊加—重套（magnitude 覆寫，不改共用法術）」與 v0.4 的「資源池：灌入、消耗、衰減都是重套這顆效果」都要加一句：DLL 先 `Dispel(true)` 舊實例再施放。自有資源池、印記、階梯的 MGEF 建議用 Script 原型。重套＝持續時間重新計滿，做不到「保留剩餘時間」。
2. **領域改走 Spawn Hazard 原型（§14）**。v0.4 §10.3 第 4 列的「PlaceObjectAtMe(HAZD) 的 owner／magnitude 不能由我們設定」要改成：用 Spawn Hazard 原型 MGEF + `CastSpellImmediate` 放置，owner、強度、壽命、上限都由引擎處理；PlaceAtMe 那條放棄。附帶的設計變化：引擎的 hazard **只打對玩家有敵意的人**，而且放在目標 actor 腳下，不能放在任意地點。
3. **N6 不需要 hook（§12）**。`design-latency` §6 N6 列的崩潰面欄要改成「背景執行緒 + 每 tick 一個 AddTask；沒有 hook」。這也讓 N5 的「放血依當下生命（若每秒點可行）」條件成立。
4. **stub 腳本只掛在低頻的「到期要結算」效果（§2）**。每擊重套的效果掛了 stub 腳本會讓 VM 每次都建物件；那些改用 tick 輪詢。
5. （提醒，非本輪範圍）v2 §18.3 建議用 SKSE cosave 存臨時資源量 `T`，和專案規則「DLL 不序列化」衝突；v0.4 已經改成「存在自有 MGEF 的強度裡」，以 v0.4 為準，v2 那段作廢。
6. 其他項目（效果移除事件、讀效果清單、死亡事件、施法狀態、中斷、範圍掃描、輸入、沖刷判定）都**不需要改設計**；v0.4 §10.3 第 1 列的後備（只靠 tick 輪詢）可以降為真正的後備。

---

## 18. 遊戲內探針（依切片分組）

每張探針都在臨時測試檔跑、跑完刪檔。「DLL log」指 `ElementsSpellblade.log`。除非特別寫，探針碼只在 debug 建置裡開。

### 共通

- **X1 執行緒（不需額外操作，附在 N3 第一個建置）**：`kDataLoaded` 時 log 主執行緒 ID；TESHitEvent、TESDeathEvent、TESActiveEffectApplyRemoveEvent、TESSpellCastEvent、輸入 sink、tick task 各在第一次觸發時 log 一次 `GetCurrentThreadId()`。玩家照常砍幾刀、殺一隻、按一次熱鍵。預期：log 裡每一行都是 `thread=<與 kDataLoaded 相同>`。若有不同，該 sink 內的讀取也改到 `AddTask`。

### N3

- **N3-1 移除事件的三種原因（約 1 分鐘）**：自家一顆掛 stub 腳本、持續 5 秒的測試 MGEF。(a) 對木樁 NPC 施放後等它到期；(b) 施放後 2 秒用控制台 `dispel`（或 DLL 測試熱鍵 `Dispel(true)`）；(c) 施放後殺掉 NPC。每次移除時 log：`found`、`elapsed`、`duration`、`magnitude`、`dead`、判定結果。預期：三次都 `found=1`；(a) `elapsed==duration → expired`；(b) `elapsed≈2 → dispel`；(c) `dead=1 → death`。另外：施放後立刻存檔、讀檔一次，看有沒有多出移除事件（記錄即可，不擋）。
- **N3-2 同一顆法術重套（約 1 分鐘）**：一顆 Value Modifier（扣血 1/秒、10 秒）和一顆 Script 原型的測試法術。DLL 測試熱鍵對同一目標連續 `CastSpellImmediate` 各 3 次（**不**先驅散），log 目標清單裡該法術的 AE 數量。預期：Script 原型永遠是 1；Value Modifier 若是 3，就證實 §5 必須先驅散（建議做法本來就先驅散，這個探針只是確認引擎行為，結果不影響實作）。
- **N3-3 沖刷判定（約 1 分鐘）**：找一名會在戰鬥中自己施放護甲術（橡木之膚、石膚）的 NPC 法師，等他施放後，再用控制台對他 `cast <另一顆增益法術> <他>`（預期是 kInstant，等同腳本施放），然後對他觸發一次沖刷。玩家自己也喝一瓶力量藥水後對自己觸發一次。log 每個 AE 的 `type/castingSource/duration/hostile/判定`。預期：只有 NPC 手部施放的護甲術被沖掉；控制台施放的、藥水、種族能力、疾病、我們的印記都留下。若控制台施放顯示的不是 `castingSource=3`，照實記錄（只影響「任務腳本」這一類的排除依據，§15 的 Papyrus 證據不變）。

### N4

- **N4-1 施法事件的消耗（沿用 v2 P1 相關）**：對一名 NPC 法師掛破魔印，讓他施放一次火球、一次專注火焰；log `CalculateMagickaCost` 與 NPC 實際掉的魔力。預期：火球兩者相等（誤差 < 1）；專注只觸發一次事件。
- **N4-2 詠唱狀態（約 1 分鐘）**：站在 NPC 法師前，DLL 每 100 ms log 他 `magicCasters[0..1]` 的 `state/castingTimer/currentSpell`。預期：舉手時 1 → 蓄力中 2（castingTimer 遞減）→ 蓄滿 3 → 放出瞬間 4/5/6 → 0；專注法術停在 6；被打斷時 9。用它確認 §8 的「正在詠唱」判定；再開一次雷滿格命中，確認 30% 中斷時 NPC 的手放下、魔力沒退。

### N5

- **N5-1 死亡事件當下的效果清單（約 1 分鐘）**：給 NPC 掛兩顆自家 MGEF（一顆一般、一顆 `kNoDeathDispel`），用 (a) 武器、(b) 我們的 DoT、(c) 控制台 `kill` 各殺一次。log 每次 `TESDeathEvent` 的 `dead`、`killer`、清單裡找到的自家 AE 數量。預期：`dead=false` 那次兩顆都找得到、killer 正確（(c) 為 null 或玩家）；`dead=true` 那次（若有）一般那顆可能已不在；(c) 若只有 `dead=true`，記下來（實作要以 `dead=true` 補判）。
- **N5-2 範圍掃描（約 1 分鐘）**：在有 5 名以上 NPC 的地方（雪漫城門口）按測試熱鍵：`AddTask` 裡掃 `highActorHandles`，log 15 公尺內的名字與距離，並對它們各施放一次無害的測試法術。預期：名單與畫面一致、不含玩家、沒有崩潰；在戰鬥中連按 10 次也不崩潰。

### N6

- **N6-1 每秒點（沿用 v2 P2）**：10 Hz tick；開 Esc 選單、背包、Alt+Tab、讀檔各 30 秒。預期：暫停時計時不前進、載入畫面時 tick 不做事、關遊戲不崩潰。
- **N6-2 熱鍵 sink（約 30 秒）**：按測試熱鍵，並在控制台、背包、MCM 文字輸入框裡各按一次。預期：只有遊戲畫面中觸發；log 的 thread 與主執行緒相同。
- **N6-3 Spawn Hazard 領域（約 1 分鐘）**：一顆 Spawn Hazard 原型 MGEF（associated item＝測試 HAZD，limit 2，lifetime 10 秒，hazard 法術扣血 1），DLL 對敵對 NPC A 的位置 `CastSpellImmediate(magnitudeOverride=5)`；旁邊站一名中立 NPC B 與隨從。連放 3 次。預期：A 每秒掉 5（不是 1）、A 轉向攻擊玩家；B 與隨從不掉血；場上最多 2 個 hazard；10 秒後自己消失；log 裡 hazard 法術的 AE `GetCasterActor()` 是玩家。任一項不符，就維持 v0.4 的後備（Papyrus 每秒領域、最多 3 個）。
