Scriptname ESSBProbeSegment extends ActiveMagicEffect

Int Property Segment Auto

Event OnEffectStart(Actor akTarget, Actor akCaster)
	Debug.Trace("[ESSB-PROBE] START segment")
	Float reported = GetMagnitude()
	Debug.Trace("[ESSB-PROBE] SEGMENT target=" + akTarget + " segment=" + Segment + " reported_magnitude=" + reported)
	Int handle = ModEvent.Create("ESSBProbeSegment18b")
	If handle
		ModEvent.PushForm(handle, akTarget)
		ModEvent.PushInt(handle, Segment)
		ModEvent.PushFloat(handle, reported)
		If !ModEvent.Send(handle)
			Debug.Trace("[ESSB-PROBE] REFUSED segment report could not be sent; restart Skyrim through SKSE with the complete probe package, then remove/add the meter on the bandit and repeat the controls")
		EndIf
	Else
		Debug.Trace("[ESSB-PROBE] REFUSED segment event could not be created; restart Skyrim through SKSE with the complete probe package, then remove/add the meter on the bandit and repeat the controls")
	EndIf
EndEvent
