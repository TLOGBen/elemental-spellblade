Scriptname ESSBPlayerAlias extends ReferenceAlias

GlobalVariable Property Enabled Auto
GlobalVariable Property DebugEnabled Auto
GlobalVariable Property AnyFormActive Auto
GlobalVariable[] Property ActiveForms Auto
Spell[] Property NormalSpells Auto
Spell[] Property PowerSpells Auto
Spell Property SettingsPower Auto

Event OnInit()
    RegisterForSingleUpdate(2.0)
EndEvent

Event OnPlayerLoadGame()
    RegisterForSingleUpdate(2.0)
EndEvent

Event OnUpdate()
    Actor caster = GetActorReference()
    If caster
        PO3_Events_Alias.RegisterForWeaponHit(Self)
        caster.AddSpell(SettingsPower, False)
        Debug.Trace("[Elements Spellblade] player alias ready; melee=" + Enabled.GetValueInt())
    EndIf
EndEvent

Event OnWeaponHit(ObjectReference akTarget, Form akSource, Projectile akProjectile, Int aiHitFlagMask)
    ; Raw RE::HitData flags, NOT the different TESHitEvent flag layout.
    ; Blocked 1, weapon block 2, bash 16384, timed bash 32768, explosion 1048576.
    If Enabled.GetValueInt() != 1 || AnyFormActive.GetValue() != 1.0
        Return
    EndIf
    If Math.LogicalAnd(aiHitFlagMask, 1097731) != 0 || akProjectile != None
        Return
    EndIf
    Weapon sourceWeapon = akSource as Weapon
    Actor targetActor = akTarget as Actor
    Actor caster = GetActorReference()
    If !sourceWeapon || !targetActor || !caster || targetActor == caster
        Return
    EndIf
    Int weaponType = sourceWeapon.GetWeaponType()
    ; 1..6 = sword/dagger/axe/mace/greatsword/battleaxe. Original Elements handles fists/bows.
    If weaponType < 1 || weaponType > 6 || targetActor.IsDead() || caster.IsDead()
        Return
    EndIf
    Int index = 0
    While index < ActiveForms.Length
        If ActiveForms[index].GetValue() == 1.0
            Spell procSpell = NormalSpells[index]
            If Math.LogicalAnd(aiHitFlagMask, 65536) != 0
                procSpell = PowerSpells[index]
            EndIf
            ; Fixed spells: no shared magnitude mutation, no physical damage rescaling,
            ; no explosions, no spawned references, no damage-to-health script bypass.
            If procSpell
                procSpell.Cast(caster, targetActor)
                If DebugEnabled.GetValueInt() == 1
                    Debug.Trace("[Elements Spellblade] weapon=" + sourceWeapon + "; target=" + targetActor + "; flags=" + aiHitFlagMask + "; spell=" + procSpell)
                EndIf
            EndIf
            Return
        EndIf
        index += 1
    EndWhile
EndEvent
