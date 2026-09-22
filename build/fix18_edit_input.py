from pathlib import Path
import re
exec(Path('build/fix18_edit_source.py').read_text(encoding='utf-8-sig').split("c=read('src/ESSBController.psc')")[0])
g=read('src/ESSBGuard.psc')
g=g.replace('ESSBController Property Ctl Auto','''GlobalVariable Property Enabled Auto
GlobalVariable Property FormActive Auto
GlobalVariable Property DivineArmed Auto
GlobalVariable Property RockArmor Auto
GlobalVariable Property IceShield Auto
GlobalVariable Property WaterMirror Auto
GlobalVariable Property GuardWind Auto
Bool Property NodeBits Auto
ESSBController Property Ctl Auto''')
g=g.replace('\tIf !Ctl || !Ctl.IsOperational()\n', '''	If !Ready || !Enabled || Enabled.GetValueInt() != 1
		Return
	EndIf
	Actor localPlayer = GetActorReference()
	Bool lethal = DivineArmed.GetValueInt() == 1 && localPlayer && localPlayer.GetActorValue("Health") <= 0.0
	If !lethal && !NodeBits && RockArmor.GetValueInt() == 0 && IceShield.GetValueInt() == 0 && WaterMirror.GetValueInt() == 0 && GuardWind.GetValueInt() == 0
		Return
	EndIf
	If !Ctl || !Ctl.IsOperational()
''',1)
g=g.replace('\tCtl.RefreshDivineProtection()','\tIf lethal\n\t\tCtl.OnLethalHitWhileArmed()\n\tEndIf',1)
g=tail(g,'Setup','\tRefreshNodeBits()')
g+='''
Function RefreshNodeBits()
	If !Ctl || !Ctl.IsCurrentController() || Ctl.StateBroken
		Return
	EndIf
	NodeBits = ESSBNodes.Br(Ctl, 11, 0, 1, 0) || ESSBNodes.Br(Ctl, 11, 1, 1, 1) || ESSBNodes.Br(Ctl, 11, 1, 3, 0) \\
		|| ESSBNodes.Br(Ctl, 0, 0, 3, 0) || ESSBNodes.Br(Ctl, 1, 0, 3, 1) || ESSBNodes.Br(Ctl, 2, 0, 1, 1) \\
		|| ESSBNodes.Br(Ctl, 3, 0, 4, 0) || ESSBNodes.Br(Ctl, 4, 0, 3, 0) \\
		|| ESSBNodes.Br(Ctl, 9, 0, 4, 0) || ESSBNodes.Br(Ctl, 7, 0, 1, 0)
EndFunction
'''
# include all retaliation nodes conservatively; correctness stronger than false-empty fast exit
for fn in ['OnEarthRetaliate','OnShadowBody','OnPoisonSkin']:
 for file in ['src/ESSBElem2.psc','src/ESSBElem3.psc']:
  txt=read(file)
  if re.search(r'Function '+fn+r'\(',txt):
   for args in re.findall(r'ESSBNodes.Br\(akCtl, ([\d, ]+)\)',body(txt,fn)):
    g=g.replace('\tNodeBits = ','\tNodeBits = ESSBNodes.Br(Ctl, '+args+') || ',1)
write('src/ESSBGuard.psc',g)
inp='''Scriptname ESSBInput extends ReferenceAlias
{Lightweight input: native GLOB publication precedes the busy Controller call.}
ESSBController Property Ctl Auto
GlobalVariable Property Enabled Auto
GlobalVariable Property CurrentElement Auto
GlobalVariable Property FormActive Auto
GlobalVariable Property HotkeysEnabled Auto
GlobalVariable[] Property Hotkeys Auto
GlobalVariable Property FormNotify Auto
GlobalVariable Property FreeOpen Auto
Bool Ready
Bool FreePass

Event OnInit()
	Setup()
EndEvent

Event OnPlayerLoadGame()
	Ready = False
	Setup()
EndEvent

Function Setup()
	If !Ctl || !Ctl.IsOperational()
		Return
	EndIf
	UnregisterForAllKeys()
	RegisterForMenu("Journal Menu")
	RefreshPermission()
	If HotkeysEnabled.GetValueInt() == 1
		Int i = 0
		While i < 11
			Int keyCode = Hotkeys[i].GetValueInt()
			If keyCode > 0
				RegisterForKey(keyCode)
			EndIf
			i += 1
		EndWhile
	EndIf
	Ready = True
EndFunction

Function RefreshPermission()
	If Ctl && Ctl.IsCurrentController() && !Ctl.StateBroken
		FreePass = Ctl.Br(12, 1, 1, 0)
	EndIf
EndFunction

Event OnMenuClose(String asMenuName)
	If asMenuName == "Journal Menu"
		Setup()
	EndIf
EndEvent

Event OnKeyDown(Int keyCode)
	If !Ready || HotkeysEnabled.GetValueInt() != 1 || Utility.IsInMenuMode() || UI.IsTextInputEnabled()
		Return
	EndIf
	Int i = 0
	While i < 11
		If Hotkeys[i].GetValueInt() == keyCode
			RequestSwitch(i + 1)
			Return
		EndIf
		i += 1
	EndWhile
EndEvent

Function RequestSwitch(Int aiElement)
	If !Ready || !Ctl || Ctl.StateBroken || aiElement < 1 || aiElement > 11 || Enabled.GetValueInt() != 1
		Return
	EndIf
	; Native quest identity check does not acquire the Controller's script lock.
	If GetOwningQuest() != ESSBState.ControllerQuest()
		Return
	EndIf
	Actor player = GetActorReference()
	If !player || player.IsDead()
		Return
	EndIf
	Int active = FormActive.GetValueInt()
	Int previous = CurrentElement.GetValueInt()
	If active == 0 && !FreePass && FreeOpen.GetValueInt() <= 0 && player.GetActorValue("Magicka") < player.GetActorValueMax("Magicka") * 0.1
		Debug.Notification("魔力不足，無法開啟形態")
		Return
	EndIf
	If active == 1 && previous == aiElement
		FormActive.SetValueInt(0)
		CurrentElement.SetValueInt(0)
	Else
		CurrentElement.SetValueInt(aiElement)
		FormActive.SetValueInt(1)
	EndIf
	If FormNotify.GetValueInt() == 1
		If FormActive.GetValueInt() == 0
			Debug.Notification("元素魔戰士：關閉形態")
		Else
			Debug.Notification("元素魔戰士：" + FormLabel(aiElement))
		EndIf
	EndIf
	; Consume the existing deadline only after publishing the engine selection.
	If active == 0
		Ctl.SetFreeOpen(0)
	EndIf
	Ctl.SwitchForm(aiElement)
EndFunction

String Function FormLabel(Int aiElement)
'''
for i,l in enumerate(['火焰','冰霜','雷電','大地','風','鮮血','神聖','毒素','水','黑暗','星界'],1):inp+=f'\t'+('If' if i==1 else 'ElseIf')+f' aiElement == {i}\n\t\tReturn "{l}"\n'
inp+='\tEndIf\n\tReturn ""\nEndFunction\n'
write('src/ESSBInput.psc',inp)
p=read('src/ESSBFormPowerEffect.psc')
p=p.replace('ESSBController controllerAlias = Controller.GetAlias(0) as ESSBController','ESSBInput controllerAlias = Controller.GetAlias(0) as ESSBInput').replace('controllerAlias && controllerAlias.IsOperational()','controllerAlias').replace('controllerAlias.ToggleForm(ElementIndex)','controllerAlias.RequestSwitch(ElementIndex)')
write('src/ESSBFormPowerEffect.psc',p)
