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
Windows (SetWindow): 30 嗜血 / 31 連殺 (player)  32 火域 / 33 冰原 / 34 星域 (target)  35 in a 火域 (player)
  36 浮空 (target; magnitude = landing damage)  37 瘋狂冷卻 (target; seconds before the MCM cooldown multiplier)
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
ClearStatus, SetWindow, ApplyMark, ExtendFuse, WashBuffs, CastProc, DumpTargets) only queues its work on the main thread
(SKSE AddTask, first in first out) and returns at once; a GetStatus right after one of them reads the state before it.
BurstMarks, SetGuided, DotRemaining, ForceOpen, EndMark, Shatter and Detonate (the Papyrus bodies' hooks) are gone.}

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
Function ExtendFuse(Float afSeconds) Global Native
Function WashBuffs(Actor akActor, Int aiLimit) Global Native
Function DumpTargets(Float afRadius) Global Native
Function CastProc(Actor akActor, Bool abPower) Global Native
Function FormEnter(Int aiElement) Global Native
Function SetSync(Int aiCount) Global Native
