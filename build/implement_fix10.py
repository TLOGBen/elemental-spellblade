"""Round 10 edits. Preserve each input's BOM/newline convention."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def edit(name, transform):
    p = ROOT / name
    raw = p.read_bytes()
    bom = raw.startswith(b'\xef\xbb\xbf')
    nl = '\r\n' if b'\r\n' in raw else '\n'
    s = raw.decode('utf-8-sig').replace('\r\n', '\n')
    out = transform(s)
    p.write_bytes((b'\xef\xbb\xbf' if bom else b'') + out.replace('\n', nl).encode('utf8'))

def ctl(s):
    s = s.replace('Int LastDamageElement', '''; FIX10: provenance belongs to the victim, never to the active form.
Int[] RegLastDamage
Actor[] DamageActor
Int[] DamageElement
Int DamageNext''')
    # Put the schema/identity check before touching old untyped member arrays.
    s = s.replace('If StateBroken\n', 'If !IsCurrentController() || StateBroken\n')
    s = s.replace('Return !StateBroken && Ready', 'Return IsCurrentController() && !StateBroken && Ready')
    s = s.replace('; FIX9: the failure latch', '''; FIX10: compare with the current alias; never call a native on an orphan alias.
Bool Function IsCurrentController()
	Quest currentQuest = ESSBState.ControllerQuest()
	If !currentQuest
		Return False
	EndIf
	ESSBController current = currentQuest.GetAlias(0) as ESSBController
	Return current == Self
EndFunction

; FIX9: the failure latch''')
    init = ''
    for name, typ, count in [('RegLastDamage','Int',8),('DamageActor','Actor',128),('DamageElement','Int',128)]:
        init += f'''\tIf !{name}
		{name} = new {typ}[{count}]
		If !{name}
			BreakState()
			Return
		EndIf
	EndIf
'''
    s = s.replace('\tFixInitialised = True', init + '\tFixInitialised = True')
    s = s.replace('\tRegActor[aiSlot] = akTarget', '\tRegLastDamage[aiSlot] = LastDamageFor(akTarget)\n\tRegActor[aiSlot] = akTarget')
    s = s.replace('\tRegActor[aiSlot] = None', '\tRegLastDamage[aiSlot] = 0\n\tRegActor[aiSlot] = None')
    old = '''Bool Function LastDamageWasElement(Int aiElement)
	Return LastDamageElement == aiElement
EndFunction

Function NoteDamageElement(Int aiElement)
	LastDamageElement = aiElement
EndFunction'''
    new = '''; The fallback also retains evidence after registry eviction/death cleanup.
Int Function LastDamageFor(Actor akTarget)
	If !akTarget || !DamageActor
		Return 0
	EndIf
	Int slot = FindSlot(akTarget)
	If slot >= 0
		Return RegLastDamage[slot]
	EndIf
	Int i = 0
	While i < 128
		If DamageActor[i] == akTarget
			Return DamageElement[i]
		EndIf
		i += 1
	EndWhile
	Return 0
EndFunction

Bool Function LastDamageWasElement(Actor akTarget, Int aiElement)
	Return LastDamageFor(akTarget) == aiElement
EndFunction

Function NoteDamageElement(Actor akTarget, Int aiElement)
	If !akTarget || !DamageActor
		Return
	EndIf
	Int slot = FindSlot(akTarget)
	If slot >= 0
		RegLastDamage[slot] = aiElement
	EndIf
	Int i = 0
	While i < 128
		If DamageActor[i] == akTarget
			DamageElement[i] = aiElement
			Return
		EndIf
		i += 1
	EndWhile
	DamageActor[DamageNext] = akTarget
	DamageElement[DamageNext] = aiElement
	DamageNext = (DamageNext + 1) % 128
EndFunction

; All damaging spells are instant contact/self delivery (DELIVERY build gate).
; Publish before native application, retain only a lethal application afterwards.
; A resisted/nonlethal holy hit must not tag a later physical/external kill.
Function ApplyTrackedDamage(Actor player, Spell akSpell, Actor akTarget, Int aiElement)
	If !IsOperational() || !player || !akSpell || !akTarget
		Return
	EndIf
	If akTarget.IsDead() || akTarget.GetActorValue("Health") <= 0.0
		Return
	EndIf
	NoteDamageElement(akTarget, aiElement)
	player.DoCombatSpellApply(akSpell, akTarget)
	If !akTarget.IsDead() && akTarget.GetActorValue("Health") > 0.0
		NoteDamageElement(akTarget, 0)
	EndIf
EndFunction'''
    assert old in s
    s = s.replace(old,new)
    s = s.replace('player.DoCombatSpellApply(procSpell, akTarget)', 'ApplyTrackedDamage(player, procSpell, akTarget, aiElement)')
    s = s.replace('player.DoCombatSpellApply(reactSpell, akTarget)\n\t; 化灰要知道「最後一次本模組傷害是哪個元素」（規劃 8 的化灰實作備註）。\n\tLastDamageElement = aiElement', 'ApplyTrackedDamage(player, reactSpell, akTarget, aiElement)')
    s = s.replace('\t\tLastDamageElement = aiElement\n\t\tplayer.DoCombatSpellApply(TrueSpell, akTarget)', '\t\tApplyTrackedDamage(player, TrueSpell, akTarget, aiElement)')
    s = s.replace('\tplayer.DoCombatSpellApply(TrueSpell, akTarget)', '\tApplyTrackedDamage(player, TrueSpell, akTarget, 0)')
    s = s.replace('\tplayer.DoCombatSpellApply(utilSpell, akTarget)', '''	If aiIndex == 7
		ApplyTrackedDamage(player, utilSpell, akTarget, 6)
	Else
		player.DoCombatSpellApply(utilSpell, akTarget)
	EndIf''')
    # Freeze provenance as a local before any on-kill AoE can overwrite another target.
    s = s.replace('\tESSBElem.OnKill(Self, element, akVictim, freeze)', '\tInt killingElement = LastDamageFor(akVictim)\n\tESSBElem.OnKill(Self, element, akVictim, freeze)')
    s = s.replace('ESSBElem2.OnKill(Self, element, akVictim, bleed)', 'ESSBElem2.OnKill(Self, element, akVictim, bleed, killingElement)')
    s = s.replace('ESSBElem3.OnKill(Self, element, akVictim, poison)', 'ESSBElem3.OnKill(Self, element, akVictim, poison, killingElement)')
    # No-form riposte cannot be carried into an active form.
    s = s.replace('\tInt previous = 0\n', '\tRiposteLeft = 0\n\tInt previous = 0\n',1)
    s = s.replace('\tIf RiposteLeft > 0\n\t\tRiposteLeft = 0\n\t\tmagnitude = magnitude * 1.3\n\tEndIf\n','')
    # Build pins these records to one-shot, including envelope variants.
    s = s.replace('; 所以 Sound.Play 不依賴 Phenderix 是否啟用。', '; FIX10: build_v03.py forces both FormActive and DrawSheathe descriptors to one-shot.\n; Release / Charge are already one-shot; no persistent instance or StopInstance is needed.')
    return s

edit('src/ESSBController.psc', ctl)

def elem2(s):
    s = re.sub(r'^\s*akCtl.NoteDamageElement\(7\)\n', '\n',s,flags=re.M)
    s = s.replace('Actor akTarget, Int aiBleed) Global', 'Actor akTarget, Int aiBleed, Int aiKillingElement = 0) Global')
    s = s.replace('ShouldAsh(akCtl, aiElement)', 'ShouldAsh(akCtl, aiKillingElement)')
    s = s.replace('If akCtl.LastDamageWasElement(7)', 'If aiElement == 7')
    s = s.replace('&& aiElement == 7 && akCtl.SyncStage()', '&& akCtl.FormActive.GetValueInt() == 1 && akCtl.CurrentElement.GetValueInt() == 7 && akCtl.SyncStage()')
    s = s.replace('最後一次本模組傷害是神聖', '本次目標的致死傷害是神聖')
    return s
edit('src/ESSBElem2.psc',elem2)

def elem3(s):
    s = re.sub(r'^\s*akCtl.NoteDamageElement\(10\)\n', '\n',s,flags=re.M)
    s = s.replace('Actor akTarget, Int aiPoison) Global', 'Actor akTarget, Int aiPoison, Int aiKillingElement = 0) Global')
    s = s.replace('akCtl.LastDamageWasElement(10) && !ESSBElem2.ShouldAsh(akCtl, aiElement)', 'aiKillingElement == 10 && !ESSBElem2.ShouldAsh(akCtl, aiKillingElement)')
    return s
edit('src/ESSBElem3.psc',elem3)

# Quarantine saved old aliases without invoking any native on those aliases.
edit('src/ESSBGuard.psc',lambda s:s.replace('If !Ctl || Ctl.StateBroken', 'If !Ctl || !Ctl.IsCurrentController() || Ctl.StateBroken'))
edit('src/ESSBTrees.psc',lambda s:s.replace('If !Controller || Controller.StateBroken', 'If !Controller || !Controller.IsCurrentController() || Controller.StateBroken'))

def nodes(s):
    for header,ret in [('Int Function Rank(', '0'),('Bool Function Br(', 'False')]:
        start=s.index(header);end=s.index('EndFunction',start)
        part=s[start:end]
        part=part.replace('\tReturn akCtl.Trees.', f'''	; 5.1 martial / anti-magic only while no form; burst route has explicit transitions.
	If aiTree == 11 && aiRoute < 2 && akCtl.FormActive.GetValueInt() == 1
		Return {ret}
	EndIf
	Return akCtl.Trees.''')
        s=s[:start]+part+s[end:]
    return s
edit('src/ESSBNodes.psc',nodes)

def builder(s):
    s=s.replace("    if shut['missing_selectors'] or shut['ambiguous_selectors']:", '''    # FIX10: these are event cues (design 2.12), never sustained ambience.
    # LNAM byte 1: 0=None, 8=Loop, 16/32=Envelope (vendor xEdit definition).
    for entry in records:
        if entry['sig'] == 'SNDR' and any(entry['edid'].startswith('ESSBFX_ZZSoundDescriptor_' + family + '_')
                                        for family in ('FormActive', 'DrawSheathe')):
            entry['ss'] = [(tag, payload[:1] + b'\\x00' + payload[2:] if tag == 'LNAM' else payload)
                           for tag, payload in entry['ss']]
    if shut['missing_selectors'] or shut['ambiguous_selectors']:''')
    s=s.replace("    runpy.run_path(str(WORK / 'build/fix9_verify.py'))['run']()", "    runpy.run_path(str(WORK / 'build/fix9_verify.py'))['run']()\n    runpy.run_path(str(WORK / 'build/fix10_verify.py'))['run']()")
    return s
edit('build_v03.py',builder)
edit('settings.json',lambda s:s.replace('"state_schema_version": 2','"state_schema_version": 3'))

if __name__ == '__main__':
    print('FIX10 sources edited; schema 3; no deployment')
