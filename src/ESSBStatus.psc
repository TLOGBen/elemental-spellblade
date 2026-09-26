Scriptname ESSBStatus extends ActiveMagicEffect
{元素狀態容器（規劃 v0.3 第 2.3、2.7 節）。

每個帶印記的目標掛一個 ESSB_StatusHost（30 秒、隱藏無傷），本腳本就是它的 AME。
規劃 2.7 的守則：**每個目標只有一個每秒計時器**，層數狀態不逐層開計時，
用環狀桶記「這一秒加了幾層」，每秒丟最舊一格，層數總和 = 各格相加。
放血（讀目標當前生命）、毒層傷害、流血傷害、星痕引爆、毒的擴散、死咒倒數
全部在同一個每秒 tick 裡做，沒有每幀迴圈、沒有 Utility.Wait。

宿主只有 30 秒，所以控制器會在 GetTimeElapsed() > 25 時換宿：
PrepareSwap() → ExportInts()/ExportFloats() → Dispel() → 重掛 → ImportState()。
換宿中的 OnEffectFinish 不回報控制器（Migrating 旗標），登記表不會被清掉。

狀態種類（aiKind，與 ESSBReactions／ESSBController 共用同一張表）：
  1 熱度 2 凍結量表 3 裂痕 4 失衡 5 血痕 6 聖印 7 毒層 8 浸濕 9 水壓 10 詛咒 11 星痕
環狀桶：血痕 10 格（命中刷新全部＝併回最新格）、毒層 12 格（每層獨立 12 秒、命中不刷新舊層）、
星痕 2 格（2 秒後自行引爆）。}

EffectShader Property FrozenShader Auto
Bool FrozenFxShown = False

Quest Property Controller Auto
{ESSB_MainQuest；玩家 ReferenceAlias 為 alias 0}

Actor Holder
ESSBController Ctl
Bool Migrating = False
Bool Bound = False
Bool Finished = False

; ---------------------------------------------------------------- 狀態本體
Int Heat
Int Freeze
Int Fissure
Int Unbalance
Int HolyStack
Int Wet
Int Pressure
Int Curse
Float CatalyzeLeft
Float DeathCurseLeft
Float SpreadCounter
Float RingClock
Bool Settling
; round 3：星鎖（5.13 開啟大師分支，3 秒）與汪洋之始（5.11 開啟傳奇分支，浸濕不過期）。
Float StarLockLeft
Int WetLock
; 浮空（規劃 8 的空中追擊實作備註）：自有狀態，不讀物理狀態。
; 由 ESSBController.LiftUp 設定，每秒倒數，到期時結算落地傷害。
Float AirLeft
Float AirDamage

Int[] BleedRing
Int[] PoisonRing
Int[] AstralRing

Float HeatTime
Float FreezeTime
Float FissureTime
Float UnbalanceTime
Float HolyTime
Float WetTime
Float PressureTime
Float CurseTime
Float NextEndMult
Float NextOpenMult
Float DeathCurseAmount
Float DeathCurseMult = 1.0
Float CatalyzeMult = 1.0
Float FreezeSeconds
Float[] AstralWeight

; ---------------------------------------------------------------- 生命週期

Event OnEffectStart(Actor akTarget, Actor akCaster)
	If Controller != ESSBState.ControllerQuest()
		Return
	EndIf
	Holder = akTarget
	If !Controller || !akTarget
		Return
	EndIf
	Ctl = Controller.GetAlias(0) as ESSBController
	If !Ctl || !Ctl.IsOperational()
		Return
	EndIf
	If !Ctl || Finished
		Return
	EndIf
	InitRings()
	If Ctl.StateBroken
		Return
	EndIf
	RingClock = Utility.GetCurrentRealTime()
	Bound = True
	Ctl.OnStatusStart(akTarget, Self)
	; Controller/Tick may finish this effect while their stack is running.
	If !Finished && !Migrating && !Ctl.StateBroken
		RegisterForSingleUpdate(1.0)
	EndIf
EndEvent

Event OnEffectFinish(Actor akTarget, Actor akCaster)
	StopFrozenFx()
	; Native binding is already gone here; the engine removes registrations.
	Finished = True
	If Migrating || !Bound || !Ctl || !Holder || Controller != ESSBState.ControllerQuest() || !Ctl.IsOperational()
		Return
	EndIf
	; A late host expiry must settle elapsed work before dropping its binding.
	If !Holder.IsDead()
		Tick()
	EndIf
	Ctl.OnStatusFinish(Holder, Self)
EndEvent

Function InitRings()
	If Ctl && Ctl.StateBroken
		Return
	EndIf
	; Also expand rings serialized in older saves, preserving each bucket's age.
	If !BleedRing || BleedRing.Length != ESSBState.BleedSeconds()
		Int[] oldBleed = BleedRing
		BleedRing = ESSBState.NewBleed()
		If !BleedRing
			Ctl.BreakState()
			Return
		EndIf
		CopyRing(oldBleed, BleedRing)
	EndIf
	If !PoisonRing || PoisonRing.Length != ESSBState.PoisonSeconds()
		Int[] oldPoison = PoisonRing
		PoisonRing = ESSBState.NewPoison()
		If !PoisonRing
			Ctl.BreakState()
			Return
		EndIf
		CopyRing(oldPoison, PoisonRing)
	EndIf
	If !AstralRing
		AstralRing = new Int[2]
		If !AstralRing
			Ctl.BreakState()
			Return
		EndIf
	EndIf
	If !AstralWeight
		AstralWeight = new Float[2]
		If !AstralWeight
			Ctl.BreakState()
			Return
		EndIf
		; Existing saves already carrying stars retain their unweighted contribution.
		AstralWeight[0] = AstralRing[0] as Float
		AstralWeight[1] = AstralRing[1] as Float
	EndIf
	If NextEndMult <= 0.0
		NextEndMult = 1.0
	EndIf
	If NextOpenMult <= 0.0
		NextOpenMult = 1.0
	EndIf
EndFunction

Function CopyRing(Int[] source, Int[] target)
	If !source
		Return
	EndIf
	Int i = 0
	While i < source.Length && i < target.Length
		target[i] = source[i]
		i += 1
	EndWhile
EndFunction

; 控制器在換宿前呼叫：停掉 tick，並讓 OnEffectFinish 不回報。
Function PrepareSwap()
	; A pending single update becomes a no-op; never unregister a dead AME.
	Migrating = True
	StopFrozenFx()
EndFunction

Function DispelIfActive()
	If !Finished
		Finished = True
		StopFrozenFx()
		Dispel()
	EndIf
EndFunction

Bool Function IsStale(Float afSeconds)
	If Finished || Migrating
		Return False
	EndIf
	Return GetTimeElapsed() > afSeconds
EndFunction

; fix round 3: visual transitions only; no extra timer and no gameplay spell.
Function SyncFrozenFx()
	If !FrozenShader || !Holder
		Return
	EndIf
	If Finished || Migrating || !Holder || Freeze < 5 || Holder.IsDead()
		StopFrozenFx()
	ElseIf !FrozenFxShown
		FrozenFxShown = True
		FrozenShader.Play(Holder)
	EndIf
EndFunction

Function StopFrozenFx()
	If FrozenFxShown
		FrozenFxShown = False
		If FrozenShader && Holder
			FrozenShader.Stop(Holder)
		EndIf
	EndIf
EndFunction

; ---------------------------------------------------------------- 環狀桶

Int Function RingSum(Int[] aiRing)
	Int total = 0
	Int index = 0
	While index < aiRing.Length
		total += aiRing[index]
		index += 1
	EndWhile
	Return total
EndFunction

; 最新的一秒在 [0]，每秒往後推一格，最後一格掉出去；回傳掉出去的層數。
Int Function RingAge(Int[] aiRing)
	Int expired = aiRing[aiRing.Length - 1]
	Int index = aiRing.Length - 1
	While index > 0
		aiRing[index] = aiRing[index - 1]
		index -= 1
	EndWhile
	aiRing[0] = 0
	Return expired
EndFunction

Function RingMerge(Int[] aiRing)
	; 血痕：命中刷新全部＝把舊格併回最新格，整批重新計時。
	Int total = RingSum(aiRing)
	Int index = 1
	While index < aiRing.Length
		aiRing[index] = 0
		index += 1
	EndWhile
	aiRing[0] = total
EndFunction

Function RingAdd(Int[] aiRing, Int aiAmount, Int aiCap)
	Int total = RingSum(aiRing)
	Int room = aiAmount
	If aiCap > 0 && total + room > aiCap
		room = aiCap - total
	EndIf
	If room > 0
		aiRing[0] = aiRing[0] + room
	EndIf
EndFunction

; ---------------------------------------------------------------- 對外：疊層與讀取

Function AddStack(Int aiKind, Int aiAmount)
	InitRings()
	If Ctl.StateBroken
		Return
	EndIf
	If RingClock > 0 && !Settling && Utility.GetCurrentRealTime() - RingClock >= 1.0 && Holder && !Holder.IsDead()
		Tick()
	ElseIf RingClock <= 0
		RingClock = Utility.GetCurrentRealTime()
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If aiKind == 1
		Heat += aiAmount
		HeatTime = now
		Int heatCap = 10
		If Ctl
			heatCap = Ctl.StackCap(1)
		EndIf
		If Heat >= heatCap
			; 規劃 2.3（v0.3 熱度在目標身上，N3 前）：熱度滿即自燃，自燃後熱度歸零。倍率在 ESSBElem。
			If Ctl && Holder
				ESSBElem.OnIgnite(Ctl, Holder, Heat)
			EndIf
			Heat = 0
		EndIf
	ElseIf aiKind == 2
		Freeze += aiAmount
		If Freeze > 5
			Freeze = 5
		EndIf
		FreezeTime = now
		SyncFrozenFx()
	ElseIf aiKind == 3
		Fissure = 1
		FissureTime = now
	ElseIf aiKind == 4
		Unbalance = 1
		UnbalanceTime = now
	ElseIf aiKind == 5
		RingMerge(BleedRing)
		RingAdd(BleedRing, aiAmount, Cap(5, 8))
	ElseIf aiKind == 6
		HolyStack += aiAmount
		Int holyCap = Cap(6, 5)
		If HolyStack > holyCap
			HolyStack = holyCap
		EndIf
		HolyTime = now
	ElseIf aiKind == 7
		; 毒層無上限，命中不刷新舊層。
		RingAdd(PoisonRing, aiAmount, 0)
	ElseIf aiKind == 8
		Wet = 1
		WetTime = now
	ElseIf aiKind == 9
		Pressure += aiAmount
		Int pressureCap = Cap(9, 5)
		If Pressure > pressureCap
			Pressure = pressureCap
		EndIf
		PressureTime = now
	ElseIf aiKind == 10
		Curse += aiAmount
		Int curseCap = Cap(10, 5)
		If Curse > curseCap
			Curse = curseCap
		EndIf
		CurseTime = now
	ElseIf aiKind == 11
		AddAstral(aiAmount, 1.0)
	EndIf
EndFunction

; 上限的三種來源（規劃 2.3）：基礎、該樹分支、通用樹傳奇主線。
; 控制器的 StackCap 已經把三者算好；拿不到控制器時退回基礎值。
Int Function Cap(Int aiKind, Int aiFallback)
	If !Ctl
		Return aiFallback
	EndIf
	Return Ctl.StackCap(aiKind)
EndFunction

; 節點要直接設定絕對層數時用（絕霜、烈火之始、冰棺、熔心殘留）。
Function SetStack(Int aiKind, Int aiValue)
	InitRings()
	If Ctl.StateBroken
		Return
	EndIf
	If RingClock > 0 && !Settling && Utility.GetCurrentRealTime() - RingClock >= 1.0 && Holder && !Holder.IsDead()
		Tick()
	ElseIf RingClock <= 0
		RingClock = Utility.GetCurrentRealTime()
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If aiKind == 1
		Heat = aiValue
		HeatTime = now
	ElseIf aiKind == 2
		Freeze = aiValue
		FreezeTime = now
		FreezeSeconds = 0.0
		SyncFrozenFx()
	ElseIf aiKind == 5
		ClearRing(BleedRing)
		RingAdd(BleedRing, aiValue, Cap(5, 8))
	ElseIf aiKind == 7
		ClearRing(PoisonRing)
		RingAdd(PoisonRing, aiValue, 0)
	ElseIf aiKind == 11
		ClearStack(11)
		AddAstral(aiValue, 1.0)
	Else
		ClearStack(aiKind)
		If aiValue > 0
			AddStack(aiKind, aiValue)
		EndIf
	EndIf
EndFunction

Int Function GetStack(Int aiKind)
	InitRings()
	If Ctl && Ctl.StateBroken
		Return 0
	EndIf
	If RingClock > 0 && !Settling && Utility.GetCurrentRealTime() - RingClock >= 1.0 && Holder && !Holder.IsDead()
		Tick()
	ElseIf RingClock <= 0
		RingClock = Utility.GetCurrentRealTime()
	EndIf
	If aiKind == 1
		Return Heat
	ElseIf aiKind == 2
		Return Freeze
	ElseIf aiKind == 3
		Return Fissure
	ElseIf aiKind == 4
		Return Unbalance
	ElseIf aiKind == 5
		Return RingSum(BleedRing)
	ElseIf aiKind == 6
		Return HolyStack
	ElseIf aiKind == 7
		Return RingSum(PoisonRing)
	ElseIf aiKind == 8
		Return Wet
	ElseIf aiKind == 9
		Return Pressure
	ElseIf aiKind == 10
		Return Curse
	ElseIf aiKind == 11
		Return RingSum(AstralRing)
	EndIf
	Return 0
EndFunction

Function ClearStack(Int aiKind)
	InitRings()
	If Ctl && Ctl.StateBroken
		Return
	EndIf
	If aiKind == 1
		Heat = 0
	ElseIf aiKind == 2
		Freeze = 0
		FreezeSeconds = 0.0
		SyncFrozenFx()
	ElseIf aiKind == 3
		Fissure = 0
	ElseIf aiKind == 4
		Unbalance = 0
	ElseIf aiKind == 5
		ClearRing(BleedRing)
	ElseIf aiKind == 6
		HolyStack = 0
	ElseIf aiKind == 7
		ClearRing(PoisonRing)
	ElseIf aiKind == 8
		Wet = 0
		WetLock = 0
	ElseIf aiKind == 9
		Pressure = 0
	ElseIf aiKind == 10
		Curse = 0
	ElseIf aiKind == 11
		ClearRing(AstralRing)
		AstralWeight[0] = 0.0
		AstralWeight[1] = 0.0
	EndIf
EndFunction

Function SetFrozen(Float afSeconds, Float afDeadline = 0.0)
	FreezeTime = Utility.GetCurrentRealTime()
	Freeze = 5
	FreezeSeconds = Ctl.DurationSeconds(afSeconds)
	If afDeadline > 0.0
		; Deadline is already scaled. Never put a start timestamp in the future.
		FreezeSeconds = afDeadline - FreezeTime
		If FreezeSeconds <= 0.0
			FreezeSeconds = 0.01
			FreezeTime = afDeadline - FreezeSeconds
		EndIf
	EndIf
	SyncFrozenFx()
EndFunction

; Weighted stars preserve exact opening multipliers without multiplying integer layers.
Function AddAstral(Int aiLayers, Float afMult)
	InitRings()
	If Ctl && Ctl.StateBroken
		Return
	EndIf
	If RingClock > 0 && !Settling && Utility.GetCurrentRealTime() - RingClock >= 1.0 && Holder && !Holder.IsDead()
		Tick()
	ElseIf RingClock <= 0
		RingClock = Utility.GetCurrentRealTime()
	EndIf
	Int capValue = Cap(11, 3)
	Int room = capValue - RingSum(AstralRing)
	If aiLayers < room
		room = aiLayers
	EndIf
	If room <= 0
		Return
	EndIf
	AstralRing[0] = AstralRing[0] + room
	AstralWeight[0] = AstralWeight[0] + room * afMult
EndFunction

Function DetonateAstralNow(Float afMult)
	InitRings()
	If Ctl && Ctl.StateBroken
		Return
	EndIf
	Int layers = RingSum(AstralRing)
	Float weight = AstralWeight[0] + AstralWeight[1]
	ClearStack(11)
	ESSBElem3.DetonateAstral(Ctl, Holder, layers, weight, afMult)
EndFunction

Function ClearRing(Int[] aiRing)
	Int index = 0
	While index < aiRing.Length
		aiRing[index] = 0
		index += 1
	EndWhile
EndFunction

; 血潮：剩餘流血總傷（每層每秒 B_max × k_dot，乘上該格還剩幾秒）。
Float Function BleedRemaining(Float afPerLayerPerSecond)
	InitRings()
	If Ctl && Ctl.StateBroken
		Return 0.0
	EndIf
	Float total = 0.0
	Int index = 0
	While index < BleedRing.Length
		total += BleedRing[index] * (BleedRing.Length - index) * afPerLayerPerSecond
		index += 1
	EndWhile
	Return total
EndFunction

; ---------------------------------------------------------------- 對外：接管與延遲效果

; ---- 浮空（5.7 關閉路線：吹上天、落地傷害、空中追擊）
Function SetAirborne(Int aiSeconds, Float afDamage, Float afDeadline = 0.0)
	aiSeconds = Ctl.DurationInt(aiSeconds)
	AirLeft = Utility.GetCurrentRealTime() + aiSeconds
	If afDeadline > 0.0
		AirLeft = afDeadline
	EndIf
	AirDamage = afDamage
EndFunction

Int Function GetAirborne()
	Return Ctl.SecondsLeft(AirLeft)
EndFunction

Function SetCatalyze(Int aiSeconds, Float afMult = 1.0, Float afDeadline = 0.0)
	aiSeconds = Ctl.DurationInt(aiSeconds)
	CatalyzeLeft = Utility.GetCurrentRealTime() + aiSeconds
	If afDeadline > 0.0
		CatalyzeLeft = afDeadline
	EndIf
	CatalyzeMult = afMult
EndFunction

Bool Function IsCatalyzed()
	Return CatalyzeLeft > Utility.GetCurrentRealTime()
EndFunction

Function SetDeathCurse(Int aiSeconds, Float afAmount, Float afMult = 1.0, Float afDeadline = 0.0)
	aiSeconds = Ctl.DurationInt(aiSeconds)
	DeathCurseLeft = Utility.GetCurrentRealTime() + aiSeconds
	If afDeadline > 0.0
		DeathCurseLeft = afDeadline
	EndIf
	DeathCurseAmount = afAmount
	DeathCurseMult = afMult
EndFunction

Bool Function HasDeathCurse()
	Return DeathCurseLeft > 0
EndFunction

; ---- 星鎖（5.13 開啟大師分支）：開印目標 N 秒內受所有元素傷 +10%。
Function SetStarLock(Int aiSeconds, Float afDeadline = 0.0)
	aiSeconds = Ctl.DurationInt(aiSeconds)
	If Utility.GetCurrentRealTime() + aiSeconds > StarLockLeft
		StarLockLeft = Utility.GetCurrentRealTime() + aiSeconds
	EndIf
	If afDeadline > 0.0
		StarLockLeft = afDeadline
	EndIf
EndFunction

Bool Function HasStarLock()
	Return StarLockLeft > Utility.GetCurrentRealTime()
EndFunction

; ---- 汪洋之始（5.11 開啟傳奇分支）：浸濕不會過期，直到被切掉（終焉時清掉）。
Function ReleaseWetLock(Bool abKeepWet = False)
	If WetLock > 0
		If abKeepWet
			WetLock = 0
			WetTime = Utility.GetCurrentRealTime()
		Else
			ClearStack(8)
		EndIf
	EndIf
EndFunction

Function SetWetLock()
	WetLock = 1
	Wet = 1
	WetTime = Utility.GetCurrentRealTime()
EndFunction

; 水的導引：接管元素的下一次終焉 ×1.5（只在被切掉時設定，見 2.6）。
Function SetNextEndMult(Float afMult)
	NextEndMult = afMult
EndFunction

Float Function TakeNextEndMult()
	Float value = NextEndMult
	If value <= 0.0
		value = 1.0
	EndIf
	NextEndMult = 1.0
	Return value
EndFunction

; 星的星落：接管元素的這次開印 ×1.5。
Function SetNextOpenMult(Float afMult)
	NextOpenMult = afMult
EndFunction

Float Function TakeNextOpenMult()
	Float value = NextOpenMult
	If value <= 0.0
		value = 1.0
	EndIf
	NextOpenMult = 1.0
	Return value
EndFunction

; ---------------------------------------------------------------- 換宿：搬家

Int[] Function ExportInts()
	InitRings()
	If Ctl && Ctl.StateBroken
		Return ESSBState.NewInts()
	EndIf
	Int[] out = ESSBState.NewInts()
	out[0] = Heat
	out[1] = Freeze
	out[2] = Fissure
	out[3] = Unbalance
	out[4] = HolyStack
	out[5] = Wet
	out[6] = Pressure
	out[7] = Curse
	Int index = 0
	While index < BleedRing.Length
		out[8 + index] = BleedRing[index]
		index += 1
	EndWhile
	index = 0
	While index < PoisonRing.Length
		out[ESSBState.PoisonOffset() + index] = PoisonRing[index]
		index += 1
	EndWhile
	out[ESSBState.TailOffset() + 0] = AstralRing[0]
	out[ESSBState.TailOffset() + 1] = AstralRing[1]
	out[ESSBState.TailOffset() + 2] = 0 ; deadlines exported as floats
	out[ESSBState.TailOffset() + 3] = 0 ; deadlines exported as floats
	out[ESSBState.TailOffset() + 4] = 0
	out[ESSBState.TailOffset() + 5] = 0 ; deadlines exported as floats
	out[ESSBState.TailOffset() + 6] = 0 ; deadlines exported as floats
	out[ESSBState.TailOffset() + 7] = WetLock
	Return out
EndFunction

Float[] Function ExportFloats()
	InitRings()
	If Ctl && Ctl.StateBroken
		Float[] empty = new Float[24]
		Return empty
	EndIf
	Float[] out = new Float[24]
	out[0] = HeatTime
	out[1] = FreezeTime
	out[2] = FissureTime
	out[3] = UnbalanceTime
	out[4] = HolyTime
	out[5] = WetTime
	out[6] = PressureTime
	out[7] = CurseTime
	out[8] = NextEndMult
	out[9] = NextOpenMult
	out[10] = DeathCurseAmount
	out[11] = AirDamage
	out[12] = DeathCurseMult
	out[13] = CatalyzeMult
	out[14] = FreezeSeconds
	out[15] = AstralWeight[0]
	out[16] = AstralWeight[1]
	out[17] = CatalyzeLeft
	out[18] = DeathCurseLeft
	out[19] = AirLeft
	out[20] = StarLockLeft
	out[21] = RingClock
	out[22] = SpreadCounter
	Return out
EndFunction

Function ImportState(Int[] aiInts, Float[] afFloats)
	InitRings()
	If Ctl && Ctl.StateBroken
		Return
	EndIf
	aiInts = ESSBState.UpgradeInts(aiInts)
	If aiInts && aiInts.Length >= ESSBState.IntCount()
		Heat = aiInts[0]
		Freeze = aiInts[1]
		Fissure = aiInts[2]
		Unbalance = aiInts[3]
		HolyStack = aiInts[4]
		Wet = aiInts[5]
		Pressure = aiInts[6]
		Curse = aiInts[7]
		Int index = 0
		While index < BleedRing.Length
			BleedRing[index] = aiInts[8 + index]
			index += 1
		EndWhile
		index = 0
		While index < PoisonRing.Length
			PoisonRing[index] = aiInts[ESSBState.PoisonOffset() + index]
			index += 1
		EndWhile
		AstralRing[0] = aiInts[ESSBState.TailOffset() + 0]
		AstralRing[1] = aiInts[ESSBState.TailOffset() + 1]
		CatalyzeLeft = aiInts[ESSBState.TailOffset() + 2]
		DeathCurseLeft = aiInts[ESSBState.TailOffset() + 3]
		SpreadCounter = aiInts[ESSBState.TailOffset() + 4]
		AirLeft = aiInts[ESSBState.TailOffset() + 5]
		StarLockLeft = aiInts[ESSBState.TailOffset() + 6]
		WetLock = aiInts[ESSBState.TailOffset() + 7]
	EndIf
	If afFloats && afFloats.Length >= 12
		HeatTime = afFloats[0]
		FreezeTime = afFloats[1]
		FissureTime = afFloats[2]
		UnbalanceTime = afFloats[3]
		HolyTime = afFloats[4]
		WetTime = afFloats[5]
		PressureTime = afFloats[6]
		CurseTime = afFloats[7]
		NextEndMult = afFloats[8]
		NextOpenMult = afFloats[9]
		DeathCurseAmount = afFloats[10]
		AirDamage = afFloats[11]
	EndIf
	; Older exports contain twelve floats; additions have safe defaults.
	DeathCurseMult = 1.0
	CatalyzeMult = 1.0
	FreezeSeconds = 0.0
	AstralWeight[0] = AstralRing[0] as Float
	AstralWeight[1] = AstralRing[1] as Float
	If afFloats && afFloats.Length >= 17
		DeathCurseMult = afFloats[12]
		CatalyzeMult = afFloats[13]
		FreezeSeconds = afFloats[14]
		AstralWeight[0] = afFloats[15]
		AstralWeight[1] = afFloats[16]
	EndIf
	If afFloats && afFloats.Length >= 24
		CatalyzeLeft = afFloats[17]
		DeathCurseLeft = afFloats[18]
		AirLeft = afFloats[19]
		StarLockLeft = afFloats[20]
		RingClock = afFloats[21]
		SpreadCounter = afFloats[22]
	EndIf
	SyncFrozenFx()
EndFunction

String Function Describe()
	Return "heat=" + Heat + " freeze=" + Freeze + " bleed=" + GetStack(5) + " poison=" + GetStack(7) \
		+ " astral=" + GetStack(11) + " curse=" + Curse + " holy=" + HolyStack + " wet=" + Wet \
		+ " fissure=" + Fissure + " catalyze=" + CatalyzeLeft + " deathcurse=" + DeathCurseLeft \
		+ " pressure=" + Pressure + " starlock=" + StarLockLeft + " wetlock=" + WetLock
EndFunction

; ---------------------------------------------------------------- 每秒 tick

Event OnUpdate()
	If Controller != ESSBState.ControllerQuest()
		Return
	EndIf
	If !Ctl || Ctl.StateBroken
		Return
	EndIf
	If Finished || Migrating
		Return
	EndIf
	If !Ctl.IsOperational()
		RegisterForSingleUpdate(1.0)
		Return
	EndIf
	If !Holder || !Ctl
		Return
	EndIf
	If Holder.IsDead()
		StopFrozenFx()
		Ctl.CaptureStatusDeath(Holder)
		; No more DOT scheduling on a corpse.
		Return
	EndIf
	Tick()
	; Controller/Tick may finish this effect while their stack is running.
	If !Finished && !Migrating && !Ctl.StateBroken
		RegisterForSingleUpdate(1.0)
	EndIf
EndEvent

Function Tick()
	If !Ctl || !Ctl.IsOperational()
		Return
	EndIf
	InitRings()
	If Ctl.StateBroken
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If Settling
		Return
	EndIf
	If RingClock <= 0.0
		RingClock = now
	EndIf
	Int elapsed = (now - RingClock) as Int
	If elapsed < 1
		Return
	EndIf
	Settling = True
	Int starDelay = ESSBElem3.AstralDelay(Ctl)
	Int bleed = 0
	Int poison = 0
	Int astral = 0
	Float starWeight = 0.0
	Float poisonWork = 0.0
	Bool catalyzed = CatalyzeLeft > RingClock
	Float venomMult = CatalyzeMult
	Int step = 0
	Int horizon = PoisonRing.Length
	If BleedRing.Length > horizon
		horizon = BleedRing.Length
	EndIf
	While step < elapsed && step < horizon
		Int layers = RingSum(PoisonRing)
		bleed += RingSum(BleedRing)
		poison += layers
		Float weight = 1.0
		Bool active = CatalyzeLeft > RingClock + step
		If active
			weight = ESSBElem3.CatalyzeRate(Ctl) * venomMult
		EndIf
		poisonWork += layers * weight * ESSBElem3.PoisonTickMult(Ctl, active)
		RingAge(BleedRing)
		RingAge(PoisonRing)
		If starDelay <= 1
			astral += RingSum(AstralRing)
			starWeight += AstralWeight[0] + AstralWeight[1]
			ClearStack(11)
		Else
			astral += RingAge(AstralRing)
			starWeight += AstralWeight[1]
			AstralWeight[1] = AstralWeight[0]
			AstralWeight[0] = 0.0
		EndIf
		step += 1
	EndWhile
	RingClock += elapsed
	If CatalyzeLeft > 0 && now >= CatalyzeLeft
		CatalyzeLeft = 0.0
		CatalyzeMult = 1.0
	EndIf

	; ---- 單層狀態與量表的過期（規劃 2.3）
	; 5.3 開啟大師分支「火種」：熱度不因未命中歸零，直到被切掉或自燃。
	If Heat > 0 && now - HeatTime >= Ctl.DurationSeconds(6.0) && !ESSBElem.HasTinder(Ctl)
		Heat = 0
	EndIf
	Float frozenSeconds = Ctl.DurationSeconds(3.0 + ESSBElem.FrozenExtraSeconds(Ctl))
	If FreezeSeconds > 0.0
		frozenSeconds = FreezeSeconds
	EndIf
	If Freeze >= 5
		; 冰封期間的強減速與「深寒」，每秒一次（5.4）。
		ESSBElem.OnFrozenTick(Ctl, Holder)
		If now - FreezeTime >= frozenSeconds
			; 冰封 N 秒後量表歸零（規劃 2.3）；「永凍」分支保留一半。
			Freeze = ESSBElem.FrozenResidual(Ctl, Freeze)
			FreezeSeconds = 0.0
			FreezeTime = now
			If Ctl.CachedDebugLevel >= 1
				Ctl.LogThrottled(1, "freeze", Holder.GetFormID() + " frozen expired residual=" + Freeze)
			EndIf
		EndIf
	ElseIf Freeze > 0 && now - FreezeTime >= Ctl.DurationSeconds(6.0)
		Freeze = 0
	EndIf
	SyncFrozenFx()
	If Fissure == 1 && now - FissureTime >= Ctl.DurationSeconds(8.0)
		Fissure = 0
	EndIf
	If Unbalance == 1 && now - UnbalanceTime >= Ctl.DurationSeconds(3.0)
		Unbalance = 0
	EndIf
	; ---- 浮空：倒數到 0 的那一秒結算落地傷害（5.7 關閉傳奇主線）。
	If AirLeft > 0
		If now >= AirLeft
			AirLeft = 0.0
		EndIf
		If AirLeft <= 0
			Ctl.OnLanding(Holder, AirDamage)
			AirDamage = 0.0
		EndIf
	EndIf
	If HolyStack > 0 && now - HolyTime >= Ctl.DurationSeconds(8.0)
		HolyStack = 0
	EndIf
	; 5.11 持續新手主線：浸濕持續 10 秒 +0.3 秒／點；
	; 開啟傳奇分支「汪洋之始」：同調三段時開印的浸濕不過期，直到被切掉。
	If Wet == 1 && WetLock == 0 && now - WetTime >= Ctl.DurationSeconds(ESSBElem3.WetSeconds(Ctl))
		Wet = 0
	EndIf
	If Pressure > 0 && now - PressureTime >= Ctl.DurationSeconds(8.0)
		Pressure = 0
	EndIf
	If Curse > 0 && now - CurseTime >= Ctl.DurationSeconds(8.0)
		Curse = 0
	EndIf
	; 5.13 開啟大師分支「星鎖」：3 秒視窗，每秒倒數。
	If StarLockLeft > 0
		If now >= StarLockLeft
			StarLockLeft = 0.0
		EndIf
	EndIf

	; ---- 流血：每層每秒 B_max(Blood) × BleedDotK × 層數 × M_mod，另加放血（當前生命百分比）
	; 5.8 持續新手主線把每層傷害 +2%／點、放血係數 +0.01%／點；大師分支「止血」低血位 ×1.5。
	If bleed > 0
		Ctl.ApplyDotDamage(6, bleed * ESSBElem2.BleedPerLayer(Ctl), Holder)
		Float percent = ESSBElem2.BleedDrainPercent(Ctl, Ctl.IsVIPTarget(Holder))
		; 放血不吃 G(L) 與抗性，只吃血位命中倍率（規劃 2.7）。
		Ctl.ApplyBleedDrain(Holder, Holder.GetActorValue("Health") * percent * bleed * Ctl.GetBloodHitMult())
	EndIf

	; ---- 毒層：每層每秒 B_max(Poison) × PoisonDotK × 層數；催毒期間每秒跳兩次
	If poison > 0
		Float venom = ESSBReactions.BaseMax(Ctl, 8) * Ctl.PoisonDotK.GetValue() * poisonWork * Ctl.GetDamageMult(8) * ESSBNodes.OmniMult(Ctl)
		Ctl.ApplyDotDamage(8, venom, Holder)
		; 擴散：≥門檻時每 N 秒傳 1 層給 3 公尺內一名敵人；催毒期間改為每秒一次。
		; 間隔、門檻與每次的目標數由 5.10 持續專精路線改（見 ESSBElem3）。
		Int interval = ESSBElem3.SpreadInterval(Ctl)
		If catalyzed
			interval = 1
		EndIf
		If poison >= ESSBElem3.SpreadThreshold(Ctl) && now >= SpreadCounter
			SpreadCounter = now + Ctl.CooldownSeconds(interval)
			Int spread = ESSBElem3.SpreadTargets(Ctl)
			Ctl.SpreadPoison(Holder, 1, spread)
		EndIf
		; 5.10 持續傳奇主線「瘟疫」：同調三段時每秒有機率額外自動擴散。
		ESSBElem3.PoisonTickHook(Ctl, Holder, poison)
	Else
		SpreadCounter = 0
	EndIf

	; ---- 星痕：每層 2 秒後自行引爆（環狀桶掉出來的那一格）；
	; 5.13 開啟新手主線「星痕延遲 -0.1 秒／點」在 10 點以上縮成 1 秒，整個桶一起引爆。
	If astral > 0
		ESSBElem3.DetonateAstral(Ctl, Holder, astral, starWeight)
		If Ctl.CachedDebugLevel >= 1
			Ctl.LogThrottled(1, "astral", Holder.GetFormID() + " detonate layers=" + astral)
		EndIf
	EndIf

	If DeathCurseLeft > 0 && now >= DeathCurseLeft
		ResolveDeathCurse(False)
	EndIf

	If Ctl.CachedDebugLevel >= 3
		If Ctl.CachedDebugLevel >= 3
			Ctl.LogThrottled(3, "status", Holder.GetFormID() + " " + Describe())
		EndIf
	EndIf
	Settling = False
EndFunction

Function ResetLoadClock()
	If !Ctl || !Ctl.IsCurrentController() || Ctl.StateBroken || Finished
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	RingClock = now
	Settling = False
	SpreadCounter = now
	If CatalyzeLeft > 0
		CatalyzeLeft = now + 1.0
	EndIf
	If DeathCurseLeft > 0
		DeathCurseLeft = now + 1.0
	EndIf
	If AirLeft > 0
		AirLeft = now + 1.0
	EndIf
	If StarLockLeft > 0
		StarLockLeft = now + 1.0
	EndIf
	HeatTime = now
	FreezeTime = now
	FissureTime = now
	UnbalanceTime = now
	HolyTime = now
	WetTime = now
	PressureTime = now
	CurseTime = now
	If !Migrating
		RegisterForSingleUpdate(1.0)
	EndIf
EndFunction

; Imported backups can have survived an application restart during a host swap.
; Same-uptime swaps retain their original timestamps and remaining durations.
Function RebaseImportedClock()
	If !Ctl || !Ctl.IsCurrentController() || Ctl.StateBroken || Finished
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If RingClock > now || HeatTime > now || FreezeTime > now || FissureTime > now || UnbalanceTime > now || HolyTime > now || WetTime > now || PressureTime > now || CurseTime > now
		ResetLoadClock()
	EndIf
EndFunction

Function ResolveDeathCurse(Bool abDead = False)
	If DeathCurseLeft <= 0
		Return
	EndIf
	Float amount = DeathCurseAmount * DeathCurseMult
	Float mult = DeathCurseMult
	DeathCurseLeft = 0
	DeathCurseAmount = 0.0
	If !abDead && !Holder.IsDead()
		Float lost = Holder.GetActorValueMax("Health") - Holder.GetActorValue("Health")
		If lost > 0.0
			amount += lost * ESSBElem3.DeathCurseLostRatio(Ctl) * Ctl.GetDamageMult(10) * mult
		EndIf
		Ctl.ApplyDamage(10, amount, Holder, 10)
	EndIf
	ESSBElem3.AfterDeathCurse(Ctl, Holder, amount)
	If Ctl.CachedDebugLevel >= 1
		Ctl.LogEvent(1, "deathcurse", "settled dead=" + abDead + " amount=" + amount)
	EndIf
EndFunction
