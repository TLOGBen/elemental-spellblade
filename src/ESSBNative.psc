Scriptname ESSBNative Hidden
{ElementsSpellblade.dll only. There is no entry-51 or script base-proc fallback.

Round 22 (slice N3): the status layer lives in engine effects the DLL applies. The Papyrus reaction bodies (until N5)
read and change those effects only through these natives; they run on the main thread (not callable from tasklets).
Status codes (the old aiKind numbering with v0.4 meanings):
  1 fire mark  2 freeze gauge (5 = frozen)  3 fissure  4 unbalance  5 bleed layers  6 divine mark (聖印)  7 poison doses
  8 soak  9 pressure  10 curse  11 star layers  12 ice crystals  13 downed  14 airborne (seconds left)  15 star lock
  16 catalysed  17 death-curse fuse  18 nether  19 frozen
  on the player: 20 heat tier (0-4)  21 聖佑 tier (0-3)  22 熔身  23 懲戒 layers (ClearStatus 23 uses them up)
  24 瘋狂冷卻 (target, 1 = cooling down)
  25 AddStatus only: spread poison doses (2.7 擴散一劑: m' = m + doses, d' = max(d - t, 12)); 7 is the hit growth (+3 s)
Windows (SetWindow): 30 嗜血 / 31 連殺 (player)  36 浮空 (target; magnitude = landing damage)
  37 瘋狂冷卻 (target; seconds before the MCM cooldown multiplier)
End reasons: 0 cut, 1 burst, 2 expiry.

Round 23 (slice N4): your own resources are engine effects on you the DLL applies (native/include/SelfLayer.h). Player
codes (GetStatus / GetStatusFloat / AddStatus / SetStatus / ClearStatus on the player):
  40 sync count (AddStatus announces a stage rise: ESSB_SyncUp + 回饋)  41 sync stage (read only)  42 charges
  43 岩甲  44 風勢  45 戰意  46 冰盾  47 共鳴層  48 闇宙  49 超載 (float, read only)  50 蓄勁
  51 「下一次融斷保留全部同調」(三重奏; ClearStatus uses it up)  52 疾電 (read only)  53 蓄能的地震加成 (float;
  ClearStatus uses it up)  54 last-hit-sneak marker on a target (read only)  55 charge cap  56 wind threshold
  57 岩甲 cap (read only)  58 護血 pool (float, read only)
FormEnter: opening a form (專一's clock, 雷臨強化, 地臨強化; round 24: every 臨, the 臨強化 branches, 臨界, 雙斷).
SetSync: the count a switch or a burst leaves (承接, 連斷, 永續, 三重奏), set without a stage rise.

Round 24 (slice N5): the reaction bodies, the fusion and the death handling are the DLL's (native/include/Reactions.h).
Burst(element): closing the form -- the one scan, every mark settled, 寂 and the 冷寂 branches.
Round 24 review fix 1: every native that scans or casts (Burst, FormEnter, FormLeave, SetSync, AddStatus, SetStatus,
ClearStatus, SetWindow, ApplyMark, CastProc, DumpTargets, RequestSwitch) only queues its work on the main thread
(SKSE AddTask, first in first out) and returns at once; a GetStatus right after one of them reads the state before it.
BurstMarks, SetGuided, DotRemaining, ForceOpen, EndMark, Shatter and Detonate (the Papyrus bodies' hooks) are gone.

Round 25 (slice N6): the per-second work, the domains and the hotkeys are the DLL's (native/include/Timer.h).
RequestSwitch(element): the form powers (Z) switch through the same function as the hotkeys -- the DLL checks the
magicka gate (blood, 順轉 and 免門檻 waive it), writes ESSB_CurrentElement / ESSB_FormActive, shows the notice and sends
ESSB_Switch back to ESSBController. SetWindow 32-35, ExtendFuse and WashBuffs (the Papyrus domains' natives) are gone.}

Bool Function IsNativeHitActive() Global Native
String Function NativeVersion() Global Native
Function SetNativeHit(Bool abEnabled) Global Native

Int Function GetStatus(Actor akActor, Int aiCode) Global Native
Float Function GetStatusFloat(Actor akActor, Int aiCode) Global Native
Function AddStatus(Actor akActor, Int aiCode, Int aiAmount) Global Native
Function SetStatus(Actor akActor, Int aiCode, Int aiValue) Global Native
Function ClearStatus(Actor akActor, Int aiCode) Global Native
Function SetWindow(Actor akActor, Int aiWindow, Float afSeconds, Float afMagnitude) Global Native
Function ApplyMark(Actor akActor, Int aiElement) Global Native
Int Function MarksOn(Actor akActor) Global Native
Function Burst(Int aiElement) Global Native
Function FormLeave(Int aiElement, Bool abBurst) Global Native
Function DumpTargets(Float afRadius) Global Native
Function CastProc(Actor akActor, Bool abPower) Global Native
Function FormEnter(Int aiElement) Global Native
Function SetSync(Int aiCount) Global Native
; round 27 (G8)：切換／開形態時 DLL 已把同調歸零並加上新形態開啟的所得；這裡把 Papyrus 規則保留的份（承接、連斷、永續、三重奏）加上去（不算升段）。
Function KeepSync(Int aiCount) Global Native
; round 27e：技能樹節點的階數與分支（DLL 直接讀玩家的 perk；取代 ESSBTrees 的快取重建）。唯讀，總開關關著也回答。
Int Function NodeRank(Int aiTree, Int aiRoute, Int aiTier) Global Native
Bool Function NodeBranch(Int aiTree, Int aiRoute, Int aiTier, Int aiIndex) Global Native
; round 27e：技能選單（StatsMenu）開啟後這條路線新買的分支（位元＝階 × 4 ＋ 第幾個）；ESSBTrees 補扣分支的另外 4 點。
Int Function BranchesGained(Int aiTree, Int aiRoute) Global Native
; round 27g（0.27.6）：選單關閉時結算一個新分支：回傳結算後的點數（夠 4 點就扣掉；不夠就退回，CSF 扣的 1 點加回來，所以比傳入的大）。
Int Function SettleBranch(Int aiAvailable) Global Native
; round 27h：選單（洗點前）的關閉——DLL 立刻把形態的全域變數歸零，融斷與形態能力在它的 task 裡做；False＝沒做（沒開或總開關關著）。
Bool Function CloseForm() Global Native
; round 27h：因為別的 task 正在跑而放棄的 task 數（MCM 狀態顯示；應該永遠是 0）。
Int Function OverlapCount() Global Native
; round 27h（探針）：Papyrus 處理了序號 aiSeq 的 DLL 事件（除錯等級 2 以上才呼叫；DLL 只讀寫計數）。
Function EventSeen(Int aiSeq) Global Native
; round 27h：技能樹點數的檢查（每棵樹：點數＋已花＝等級），選單關閉與讀檔時；DLL 在 task 裡讀 perk，寫 [ESSB][pts]。
Function CheckPoints() Global Native
; round 27h（Papyrus 審查 1）：洗點——回答這棵樹有幾個節點（DLL 的快照），在 task 裡全部拿掉並把點數設回等級；-1＝沒做（總開關關著）。
Int Function RespecTree(Int aiTree) Global Native
; round 27h（Papyrus 審查 6）：百毒不侵——15 公尺內最近 5 個敵人裡中毒的有幾個（DLL 每秒數好）。
Int Function PoisonedNearby() Global Native
; round 27h（Papyrus 審查 7）：用這次的強度（0＝紀錄的）與秒數施放本模組的單一效果法術（不改共用的法術紀錄）。
Function CastWith(Spell akSpell, Actor akTarget, Float afMagnitude, Float afSeconds) Global Native
; round 27h（探針卷站 92 故障演練）：除錯等級 4 才有作用。1＝強制一個 C++ 例外（這次遊戲的故障），2＝一個壞數值（丟棄，不故障）。
Function ForceFault(Int aiKind) Global Native
Function RequestSwitch(Int aiElement) Global Native
; round 25 審查修正：遊戲在跑的秒數（這次開遊戲以來；暫停、讀檔不算）。控制器的秒計時器用它。
Float Function RunningSeconds() Global Native
; round 26：探針 log（除錯等級 4）的 Papyrus 那一半——一行 [ESSB][T][pap] kind=… who=名字(0xFormID)[生命／魔力／耐力] 文字，
; 跟 DLL 的行同一個序號寫進 ElementsSpellblade.log。只在等級 4 時呼叫（呼叫端先看等級）；唯讀。
Function Trace(String asKind, Actor akActor, String asText) Global Native
