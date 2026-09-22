Scriptname ESSBProbeSetup extends ReferenceAlias

Spell Property PreparePower Auto
Spell Property SecondPower Auto
Spell Property FourthPower Auto
Int TieNext
Perk Property TieA Auto
Perk Property TieB Auto
Perk Property TieA2 Auto
Perk Property TieB2 Auto
GlobalVariable Property TieVariant Auto
GlobalVariable Property TieResult1 Auto
GlobalVariable Property TieResult2 Auto
GlobalVariable Property TieResult3 Auto
GlobalVariable Property TieResult4 Auto
Spell Property ThirdPower Auto
Spell Property CleanupPower Auto
Spell Property Meter Auto
Perk Property ProbeAB Auto
Perk Property ProbeHit Auto
Perk Property ProbeMultiply Auto
Perk Property CrossA Auto
Perk Property CrossB Auto
Perk Property CrossA2 Auto
Perk Property CrossB2 Auto
Bool CrossSecond
Weapon Property Dagger Auto
ActorBase Property BanditBase Auto
GlobalVariable Property Gate Auto
GlobalVariable Property Session Auto
Actor Bandit
Float SavedAttackDamageMult
Bool SavedAttack
Bool Busy

Event OnInit()
	GrantPowers()
EndEvent

Event OnPlayerLoadGame()
	; SavedAttack and the original value survive reloads and repeated preparation.
	GrantPowers()
EndEvent

Function GrantPowers()
	Actor player = Game.GetPlayer()
	player.AddSpell(PreparePower, False)
	player.AddSpell(SecondPower, False)
	player.AddSpell(ThirdPower, False)
	player.AddSpell(FourthPower, False)
	player.AddSpell(CleanupPower, False)
	Debug.Notification("探針能力已加入：請收藏「準備＋第一題」、「第二題」、「第三題」、「第四題」、「清理」。")
EndFunction

Function RemovePerks(Actor player)
	player.RemovePerk(ProbeAB)
	player.RemovePerk(ProbeHit)
	player.RemovePerk(ProbeMultiply)
	player.RemovePerk(CrossA)
	player.RemovePerk(CrossB)
	player.RemovePerk(CrossA2)
	player.RemovePerk(CrossB2)
	player.RemovePerk(TieA)
	player.RemovePerk(TieB)
	player.RemovePerk(TieA2)
	player.RemovePerk(TieB2)
EndFunction

Function StopMeter(Actor player)
	Gate.SetValue(0.0)
	Session.SetValue(Session.GetValue() + 1.0)
	; Also clean an accidental meter left on the player by the console appendix.
	player.RemoveSpell(Meter)
	If Bandit && Bandit != player
		Bandit.RemoveSpell(Meter)
	EndIf
	; Allow the removed effect to finish before starting a fresh meter session.
	Utility.Wait(1.0)
EndFunction

Function DeleteBandit(Actor player)
	If Bandit && Bandit != player
		Bandit.RemoveSpell(Meter)
		Bandit.Disable()
		Bandit.Delete()
	EndIf
	Bandit = None
EndFunction

Bool Function PrepareBandit(Actor player, Bool fresh)
	If Bandit == player
		Bandit = None
	EndIf
	If Bandit
		If fresh || Bandit.IsDead() || Bandit.IsDisabled() || Bandit.IsDeleted()
			DeleteBandit(player)
		EndIf
	EndIf
	If !Bandit
		; Create disabled for placement; restrain as soon as the enabled 3D is ready.
		Bandit = player.PlaceAtMe(BanditBase, 1, True, True) as Actor
	EndIf
	If !Bandit || Bandit == player
		Bandit = None
		Return False
	EndIf
	Float angle = player.GetAngleZ()
	Bandit.MoveTo(player, Math.Sin(angle) * 128.0, Math.Cos(angle) * 128.0, 0.0)
	Bandit.Enable()
	Int loaded = 0
	While !Bandit.Is3DLoaded() && loaded < 40
		Utility.Wait(0.25)
		loaded += 1
	EndWhile
	If !Bandit.Is3DLoaded() || Bandit.IsDead() || Bandit.IsDisabled()
		Return False
	EndIf
	; Keep animation/AI processing alive: disabling AI before 3D broke melee hits.
	Bandit.EnableAI(True)
	Bandit.SetRestrained(True)
	Bandit.SetDontMove(True)
	Bandit.SetGhost(False)
	Bandit.SetActorValue("Aggression", 0.0)
	Bandit.StopCombat()
	Bandit.StopCombatAlarm()
	Bandit.SetAngle(0.0, 0.0, angle + 180.0)
	Utility.Wait(2.0)
	Bandit.UnequipAll()
	Bandit.RemoveAllItems()
	Return SettleBandit()
EndFunction

Function NetValue(String name, Float wanted)
	; Add only the CURRENT residual. Repeated calls cannot accumulate -33 offsets.
	Float residual = wanted - Bandit.GetActorValue(name)
	If residual != 0.0
		Bandit.ModActorValue(name, residual)
	EndIf
EndFunction

Bool Function SetupReady()
	Return Bandit && Bandit != Game.GetPlayer() && Bandit.Is3DLoaded() && !Bandit.IsDead() && !Bandit.IsDisabled() && !Bandit.IsDeleted() && Bandit.GetActorValue("Health") == 10000.0 && Bandit.GetActorValueMax("Health") == 10000.0 && Bandit.GetActorValue("FireResist") == 0.0 && Bandit.GetActorValue("MagicResist") == 0.0 && Bandit.GetActorValue("AbsorbChance") == 0.0 && Bandit.GetActorValue("HealRate") == 0.0 && Bandit.GetActorValue("HealRateMult") == 0.0
EndFunction

Bool Function SettleBandit()
	Int stable = 0
	Int attempts = 0
	While stable < 6 && attempts < 30
		If !Bandit.Is3DLoaded() || Bandit.IsDead() || Bandit.IsDisabled() || Bandit.IsDeleted()
			Return False
		EndIf
		Bool wasReady = SetupReady()
		NetValue("FireResist", 0.0)
		NetValue("MagicResist", 0.0)
		NetValue("AbsorbChance", 0.0)
		NetValue("HealRate", 0.0)
		NetValue("HealRateMult", 0.0)
		Float healthResidual = 10000.0 - Bandit.GetActorValueMax("Health")
		If healthResidual != 0.0
			Bandit.ModActorValue("Health", healthResidual)
		EndIf
		Bandit.RestoreActorValue("Health", 10000.0)
		Utility.Wait(0.5)
		If wasReady && SetupReady()
			stable += 1
		Else
			stable = 0
		EndIf
		attempts += 1
	EndWhile
	Debug.Trace("[ESSB-PROBE] SETTLE stable_samples=" + stable + " attempts=" + attempts + " health=" + Bandit.GetActorValue("Health") + " max_health=" + Bandit.GetActorValueMax("Health") + " fire_resist=" + Bandit.GetActorValue("FireResist") + "; AI enabled; restrained/dont-move; non-ghost")
	Return stable >= 6 && SetupReady()
EndFunction

Function LogSetup(String action, Actor target, Actor player)
	Debug.Trace("[ESSB-PROBE] SETUP " + action + " bandit=" + target + " ESSB_ProbeAB=" + player.HasPerk(ProbeAB) + " ESSB_ProbeMagnitudeHit=" + player.HasPerk(ProbeHit) + " ESSB_ProbeMultiply=" + player.HasPerk(ProbeMultiply) + " CrossA=" + player.HasPerk(CrossA) + " CrossB=" + player.HasPerk(CrossB) + " CrossA2=" + player.HasPerk(CrossA2) + " CrossB2=" + player.HasPerk(CrossB2) + " cross_variant2=" + CrossSecond + " AttackDamageMult=" + player.GetActorValue("AttackDamageMult"))
EndFunction

Function RunProbe(Int mode)
	Actor player = Game.GetPlayer()
	If Busy
		LogSetup("BUSY requested=" + mode + "; wait then cast again", Bandit, player)
		Debug.Notification("探針仍在準備或清理，請稍候再施放。")
		Return
	EndIf
	Busy = True
	StopMeter(player)
	RemovePerks(player)
	If mode == 3
		CrossSecond = False
		TieNext = 0
		ResetTie()
		player.RemoveSpell(FourthPower)
		player.RemoveSpell(ThirdPower)
		Actor removed = Bandit
		DeleteBandit(player)
		If SavedAttack
			player.ForceActorValue("AttackDamageMult", SavedAttackDamageMult)
			SavedAttack = False
		EndIf
		LogSetup("CLEANUP deleted target; meter/perks removed; attack restored", removed, player)
		Debug.Notification("探針已清理：強盜、量測器及探針 perk 已移除，攻擊倍率已還原，第三、四題能力已移除；讀檔會補發。可離開測試檔。")
	ElseIf mode == 1 || mode == 2 || mode == 4 || mode == 5
		If !SavedAttack
			SavedAttackDamageMult = player.GetActorValue("AttackDamageMult")
			SavedAttack = True
		EndIf
		player.UnequipAll()
		If player.GetItemCount(Dagger) < 1
			player.AddItem(Dagger, 1, True)
		EndIf
		player.EquipItem(Dagger, False, True)
		player.ForceActorValue("AttackDamageMult", 0.0)
		If PrepareBandit(player, mode == 1) && Bandit && Bandit != player
			If mode == 1
				player.AddPerk(ProbeAB)
			ElseIf mode == 2
				player.AddPerk(ProbeHit)
				player.AddPerk(ProbeMultiply)
			ElseIf mode == 5
				SetupTie(player)
			Else
				If !CrossSecond
					player.AddPerk(CrossA)
					player.AddPerk(CrossB)
				Else
					player.AddPerk(CrossA2)
					player.AddPerk(CrossB2)
				EndIf
			EndIf
			; Last gate immediately before attaching; no latent repair during measurement.
			If !SetupReady()
				RemovePerks(player)
				LogSetup("FAILED final AV/3D check; rerun preparation", Bandit, player)
				Debug.Notification("目標尚未穩定，未掛載量測器；請重新準備。")
				Busy = False
				Return
			EndIf
			Bool attached = Bandit.AddSpell(Meter, False)
			If mode == 5
				LogSetup("PROBE=4 variant=" + (TieNext + 1) + " priority=0/0; v1 A-low/first; v2 A-high/first; v3 A-low/last; v4 A-high/last; fresh_meter=" + attached, Bandit, player)
			ElseIf mode == 4
				LogSetup("PROBE=3 variant2=" + CrossSecond + " prepared; fresh_meter=" + attached, Bandit, player)
			Else
				LogSetup("PROBE=" + mode + " prepared; fresh_meter=" + attached, Bandit, player)
			EndIf
			If attached
				If mode == 5
					TieNext += 1
					If TieNext >= 4
						TieNext = 0
					EndIf
					mode = 4
				ElseIf mode == 4
					CrossSecond = !CrossSecond
					mode = 3
				EndIf
				Debug.Notification("第" + mode + "題：等 READY CONTROL，用匕首砍一刀，然後等；READY PROBE 再砍一刀。")
			Else
				Debug.Notification("量測器掛載失敗：請施放「清理」，再施放「準備＋第一題」。")
			EndIf
		Else
			LogSetup("FAILED spawn/3D/settle; cast cleanup then prepare again", Bandit, player)
			Debug.Notification("探針強盜建立失敗：請施放「清理」，移到空曠處再準備。")
		EndIf
	Else
		LogSetup("REFUSED unknown power mode=" + mode, Bandit, player)
		Debug.Notification("探針能力設定錯誤，請更新完整探針包。")
	EndIf
	Busy = False
EndFunction

Function ResetTie()
	If TieVariant
		TieVariant.SetValue(0.0)
		TieResult1.SetValue(0.0)
		TieResult2.SetValue(0.0)
		TieResult3.SetValue(0.0)
		TieResult4.SetValue(0.0)
	EndIf
EndFunction

Function SetupTie(Actor player)
	If TieNext == 0
		ResetTie()
	EndIf
	TieVariant.SetValue(TieNext + 1)
	Perk a = TieA
	Perk b = TieB
	If TieNext == 1 || TieNext == 3
		a = TieA2
		b = TieB2
	EndIf
	If TieNext < 2
		player.AddPerk(a)
		player.AddPerk(b)
	Else
		player.AddPerk(b)
		player.AddPerk(a)
	EndIf
EndFunction
