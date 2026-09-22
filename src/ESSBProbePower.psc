Scriptname ESSBProbePower extends ActiveMagicEffect

ESSBProbeSetup Property Setup Auto
Int Property Mode Auto

Event OnEffectStart(Actor akTarget, Actor akCaster)
	If akTarget == Game.GetPlayer() && akCaster == Game.GetPlayer()
		Setup.RunProbe(Mode)
	EndIf
EndEvent
