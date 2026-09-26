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
End reasons: 0 cut, 1 burst, 2 expiry.}

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
Int Function BurstMarks(Float afRadius, Float afMult) Global Native
Function FormLeave(Int aiElement, Bool abBurst) Global Native
Function ExtendFuse(Float afSeconds) Global Native
Function SetGuided(Actor akActor, Float afMult) Global Native
Int Function WashBuffs(Actor akActor, Int aiLimit) Global Native
Float Function DotRemaining(Actor akActor, Bool abPoison) Global Native
Actor[] Function MarkedNear(ObjectReference akCenter, Float afRadius, Int aiLimit, Int aiElement) Global Native
Function ForceOpen(Actor akActor, Int aiElement) Global Native
Function EndMark(Actor akActor, Int aiElement, Int aiReason, Float afMult) Global Native
Function CastProc(Actor akActor, Bool abPower) Global Native
Function Shatter(Actor akActor) Global Native
Function Detonate(Actor akActor) Global Native
