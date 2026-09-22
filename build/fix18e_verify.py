"""Execute actual setup PSC with native mocks; read back quest/power wiring and PEX."""
from pathlib import Path
from types import SimpleNamespace as NS
import hashlib
import json
import math
import re
import runpy
import struct
import sys


def run(b):
    sys.path.insert(0, str(b.WORK/'build'))
    from papyrus_harness import Script
    from fix18e_records import POWERS, QUEST, quest_vmad, setup_props
    folder = b.WORK/'build/fix18-probe-package'
    logs, notifications, events, spawned = [], [], [], []
    class Global:
        def __init__(self): self.value = 0.0
        def GetValue(self): return self.value
        def SetValue(self, value): self.value = value
    class Actor:
        def __init__(self, name):
            self.name = name
            self.perks, self.spells, self.items = set(), set(), {}
            self.av = {'AttackDamageMult': 1.375, 'Health': 25.0}
            self.dead = self.disabled = self.deleted = False
            self.ai = self.combat = self.gear = True
            self.restrained = self.dontmove = False
            self.ghost = True
            self.maxhealth = 25.0
            self.age = 0.0
            self.injected = False
            self.alarm = True
            self.angle = 0
            self.equipped = None
        def __str__(self): return self.name
        def AddSpell(self, spell, silent):
            if spell == 'Meter':
                assert self is not player, 'METER MUST NEVER BE ADDED TO PLAYER'
                prepared(self)
                assert player.perks in ({'ProbeAB'}, {'ProbeHit', 'ProbeMultiply'}, {'CrossA','CrossB'}, {'CrossA2','CrossB2'})
                assert player.GetActorValue('AttackDamageMult') == 0
                assert player.equipped == 'Dagger'
                events.append(('meter-add', self.name))
            self.spells.add(spell)
            return True
        def RemoveSpell(self, spell):
            self.spells.discard(spell)
            events.append(('meter-remove', self.name))
        def HasPerk(self, perk): return perk in self.perks
        def AddPerk(self, perk): self.perks.add(perk)
        def RemovePerk(self, perk): self.perks.discard(perk)
        def GetActorValue(self, name): return self.av.get(name, 50.0)
        def ForceActorValue(self, name, value):
            assert self is player, 'target must not use ForceActorValue'
            self.av[name] = value
        def SetActorValue(self, name, value): self.av[name] = value
        def GetActorValueMax(self, name): return self.maxhealth
        def ModActorValue(self, name, value):
            self.av[name] = self.GetActorValue(name) + value
            if name == 'Health': self.maxhealth += value
        def Is3DLoaded(self): return not self.disabled and self.age >= 0.5
        def SetRestrained(self, value):
            assert self.Is3DLoaded()
            self.restrained = value
        def SetDontMove(self, value):
            assert self.Is3DLoaded()
            self.dontmove = value
        def SetGhost(self, value): self.ghost = value
        def RestoreActorValue(self, name, value):
            assert name == 'Health' and value == 10000
            self.restored = True
            self.av[name] = min(self.maxhealth, self.GetActorValue(name)+value)
        def GetItemCount(self, item): return self.items.get(item, 0)
        def AddItem(self, item, count, silent): self.items[item] = self.items.get(item, 0)+count
        def EquipItem(self, item, locked, silent): self.equipped = item
        def UnequipAll(self): self.gear = False
        def RemoveAllItems(self): self.items.clear()
        def EnableAI(self, value): self.ai = value
        def StopCombat(self): self.combat = False
        def StopCombatAlarm(self): self.alarm = False
        def IsDead(self): return self.dead
        def IsDisabled(self): return self.disabled
        def IsDeleted(self): return self.deleted
        def Disable(self):
            assert self is not player
            self.disabled = True
        def Delete(self):
            assert self is not player and self.disabled and 'Meter' not in self.spells
            self.deleted = True
        def Enable(self):
            assert self is not player and self.ai
            self.disabled = False
        def GetAngleZ(self): return self.angle
        def MoveTo(self, target, x, y, z):
            assert target is player and self is not player
            self.position = (x, y, z)
        def SetAngle(self, x, y, z): self.angle = z
        def PlaceAtMe(self, base, count, persistent, disabled):
            assert self is player and base == 'BanditBase' and count == 1 and persistent and disabled
            target = Actor('bandit-'+str(len(spawned)+1))
            target.disabled = True
            target.items = {'armor': 1, 'weapon': 1}
            spawned.append(target)
            return target
    def prepared(target):
        assert target is not player and target.ai and not target.combat and not target.alarm
        assert target.Is3DLoaded() and target.restrained and target.dontmove and not target.ghost
        assert target.injected and target.maxhealth == 10000
        assert not target.gear and not target.items and target.restored
        assert target.av['Health'] == 10000
        assert all(target.av[n] == 0 for n in ('FireResist','MagicResist','AbsorbChance','HealRate','HealRateMult','Aggression'))
        x, y, z = target.position
        assert abs(math.hypot(x, y)-128) < 1e-6 and z == 0
        assert abs(x-128*math.sin(math.radians(player.angle))) < 1e-6
        assert abs(y-128*math.cos(math.radians(player.angle))) < 1e-6
    player = Actor('player')
    def wait(duration):
        events.append(('wait', duration))
        for target in spawned:
            if target.disabled or target.deleted: continue
            target.age += duration
            # Late ability lands after the first normalization, including +50 max HP.
            if target.age >= 3.0 and not target.injected:
                target.av['FireResist'] = target.GetActorValue('FireResist')+33
                target.maxhealth += 50
                target.av['Health'] += 50
                target.injected = True
    env = dict(__execute_logs__=True, __papyrus_concat__=True,
               Game=NS(GetPlayer=lambda: player), Debug=NS(Trace=logs.append, Notification=notifications.append),
               Utility=NS(Wait=wait),
               Math=NS(Sin=lambda angle: math.sin(math.radians(angle)), Cos=lambda angle: math.cos(math.radians(angle))))
    setup = Script(b.WORK/'src/ESSBProbeSetup.psc', env)
    setup.fields.update({name: name for name in setup_props(b)})
    setup.fields.update(Gate=Global(), Session=Global(), **{n: Global() for n in setup_props(b) if n=='TieVariant' or n.startswith('TieResult')})
    power = Script(b.WORK/'src/ESSBProbePower.psc', env)
    power.fields['Setup'] = setup
    rows = []
    def cast(mode, label):
        before_logs, before_notifications = len(logs), len(notifications)
        power.fields['Mode'] = mode
        power.OnEffectStart(player, player)
        assert len(logs) >= before_logs+1 and logs[-1].startswith('[ESSB-PROBE] SETUP ')
        assert all(name+'=' in logs[-1] for name in ('ESSB_ProbeAB', 'ESSB_ProbeMagnitudeHit', 'ESSB_ProbeMultiply'))
        assert 'bandit=' in logs[-1] and len(notifications) == before_notifications+1
        assert not setup.Busy and 'Meter' not in player.spells
        rows.append(dict(case=label, log=logs[-1], notification=notifications[-1]))
    setup.OnInit()
    assert player.spells == {'PreparePower', 'SecondPower', 'ThirdPower', 'FourthPower', 'CleanupPower'}
    setup.OnPlayerLoadGame()
    assert len(player.spells) == 5 and not setup.SavedAttack
    cast(3, 'cleanup before preparation leaves original AV')
    assert player.av['AttackDamageMult'] == 1.375
    cast(1, 'first preparation')
    first = setup.Bandit
    assert player.perks == {'ProbeAB'} and setup.SavedAttackDamageMult == 1.375
    assert player.items['Dagger'] == 1 and 'Meter' in first.spells
    setup.OnPlayerLoadGame()
    assert setup.SavedAttackDamageMult == 1.375 and setup.SavedAttack
    cast(2, 'second probe reuses same alive bandit after reload')
    assert setup.Bandit is first and player.perks == {'ProbeHit', 'ProbeMultiply'}
    assert events.count(('meter-add', first.name)) == 2
    first.dead = True
    cast(2, 'second probe replaces dead target')
    assert first.deleted and setup.Bandit is not first
    second = setup.Bandit
    second.disabled = True
    cast(2, 'second probe replaces disabled target')
    assert second.deleted
    third = setup.Bandit
    third.deleted = True
    cast(2, 'second probe replaces externally deleted target')
    assert setup.Bandit is not third
    previous = setup.Bandit
    player.angle = 90
    cast(1, 'repeat preparation replaces target; does not overwrite saved AV')
    assert previous.deleted and setup.SavedAttackDamageMult == 1.375 and player.items['Dagger'] == 1
    cast(4, 'third question variant 1')
    assert player.perks == {'CrossA','CrossB'}
    cast(4, 'third question variant 2')
    assert player.perks == {'CrossA2','CrossB2'}
    cast(4, 'third question repeats variant 1')
    assert player.perks == {'CrossA','CrossB'}
    cast(3, 'cleanup after repeated preparations')
    assert 'ThirdPower' not in player.spells
    assert not setup.Bandit and not setup.SavedAttack and player.av['AttackDamageMult'] == 1.375
    assert not player.perks and all(t.deleted and 'Meter' not in t.spells for t in spawned)
    cast(3, 'idempotent cleanup')
    assert player.av['AttackDamageMult'] == 1.375
    player.av['AttackDamageMult'] = 2.75
    cast(2, 'second power first creates fully prepared bandit')
    assert player.perks == {'ProbeHit','ProbeMultiply'} and setup.SavedAttackDamageMult == 2.75
    cast(3, 'new run restores its own original AV')
    assert player.av['AttackDamageMult'] == 2.75
    for angle in (0, 180, 270):
        player.angle = angle
        cast(1, 'front placement angle '+str(angle))
        prepared(setup.Bandit)
        cast(3, 'cleanup angle '+str(angle))
    # Simulate malformed/stale player reference: never prep, delete or meter player.
    setup.fields['Bandit'] = player
    player.spells.add('Meter')
    cast(2, 'player reference rejected and replaced safely')
    assert setup.Bandit is not player and not player.deleted and player.ai
    cast(3, 'cleanup guarded recovery')
    setup.fields['Bandit'] = player
    cast(3, 'cleanup with player reference cannot delete player')
    assert not player.deleted and player.ai
    # A missing/failed spawn must not grant perks or attach anything.
    original_spawn = player.PlaceAtMe
    for result in (None, player):
        player.PlaceAtMe = lambda *args: result
        cast(1, 'failed or invalid spawn')
        assert not player.perks and not setup.Bandit and 'FAILED spawn' in logs[-1]
        cast(3, 'cleanup restores AV after failed spawn')
        assert player.av['AttackDamageMult'] == 2.75
    player.PlaceAtMe = original_spawn
    original_add = Actor.AddSpell
    Actor.AddSpell = lambda target, spell, silent: False if spell == 'Meter' else original_add(target, spell, silent)
    cast(1, 'meter attachment failure is explicit')
    assert 'fresh_meter=False' in logs[-1] and '量測器掛載失敗' in notifications[-1]
    cast(3, 'cleanup after attachment failure')
    Actor.AddSpell = original_add
    # Re-entry while a latent cleanup is running is rejected without mutation.
    setup.fields['Busy'] = True
    before = (len(spawned), setup.Session.value, player.av.copy())
    setup.RunProbe(1)
    assert 'SETUP BUSY' in logs[-1] and before == (len(spawned), setup.Session.value, player.av)
    setup.fields['Busy'] = False
    before = len(logs)
    power.OnEffectStart(spawned[0], player)
    power.OnEffectStart(player, spawned[0])
    assert len(logs) == before
    # Meter/segment source bytes are not edited by this round.
    for name in ('ESSBProbeSegment',):
        assert (b.WORK/'src'/f'{name}.psc').read_bytes() == (b.WORK/'build/round18e/before/src'/f'{name}.psc').read_bytes()
    records, meta = b.read_plugin(folder/'Elements Spellblade Round18 Probes.esp')
    by = {r.edid: r for r in records}
    assert len(records) == 40 and meta['masters'] == ['Skyrim.esm']
    quest = by['ESSB_ProbeSetupQuest']
    assert quest.sig == 'QUST' and quest.d['VMAD'] == quest_vmad(b)
    assert quest.d['ALFR'] == b.I(0x14) and quest.d['ALST'] == b.I(0)
    assert struct.unpack_from('<H', quest.d['DNAM'])[0] == 0x11
    assert (folder/'SEQ/Elements Spellblade Round18 Probes.seq').read_bytes() == b.I(b.own(QUEST))
    for mode, spell, effect, edid, label in POWERS:
        power_record, effect_record = by[edid], by[edid+'Effect']
        assert power_record.name == label
        assert power_record.d['ETYP'] == b.I(0x25bee) and power_record.d['SPIT'] == b.spit(3,1,0)
        assert power_record.d['EFID'] == b.I(b.own(effect))
        assert power_record.d['EFIT'] == struct.pack('<fII',0,0,1)
        assert effect_record.d['VMAD'] == b.vmad('ESSBProbePower', {'Setup': (1,(b.own(QUEST),0)), 'Mode': (3,mode)})
        assert effect_record.d['DATA'] == b.mgef_data(b.MGEF_UTILITY_FLAGS,1,casting=1,delivery=0)
    parser = runpy.run_path(str(b.WORK/'build/fix5_read_bsa.py'))['Pex']
    pex_checks = {}
    for name in ('ESSBProbeSetup','ESSBProbePower'):
        assert name not in b.SCRIPTS
        assert (folder/'Source/Scripts'/f'{name}.psc').read_bytes() == (b.WORK/'src'/f'{name}.psc').read_bytes()
        parsed = parser((folder/'Scripts'/f'{name}.pex').read_bytes())
        tree = parsed.read()
        # Verify Chinese literals survived compiler decoding and PEX UTF-8 output.
        literals = re.findall(r'"([^"\n]*)"', (b.WORK/'src'/f'{name}.psc').read_text(encoding='utf8'))
        for literal in literals:
            if any(ord(c) > 127 for c in literal): assert literal in parsed.strings, literal
        funcs = tree['objects'][0]['states']['']
        expected = ('OnInit','OnPlayerLoadGame','GrantPowers','RunProbe','PrepareBandit','DeleteBandit') if name.endswith('Setup') else ('OnEffectStart',)
        assert all(key in funcs for key in expected)
        pex_checks[name] = list(expected)
    # Resolve the exact vanilla bases/equip slot from the permitted local master.
    vanilla, _ = b.read_plugin(b.ROOT/'SkyrimSE/Data/Skyrim.esm', {'NPC_','WEAP','EQUP'})
    vanilla_by_id = {int(r.key.split('|')[1],16): r for r in vanilla}
    assert vanilla_by_id[0xc3ca0].edid == 'EncBandit01Melee1HKhajiitM'
    assert vanilla_by_id[0x1397e].edid == 'IronDagger'
    assert vanilla_by_id[0x25bee].sig == 'EQUP'
    report = dict(actual_psc_executed=True, native_boundaries='mocked; no game execution',
                  cases=rows, pex_functions=pex_checks, segment_source_unchanged=True,
                  records=40, masters=meta['masters'], runtime_tested=False)
    (folder/'setup-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'PROBE-SETUP ok: {len(rows)} actual PSC flows; init/load grants; prepared bandit; perk sets; never meter/delete player; saved AV restore; repeat/dead/missing/reentry; QUST/SEQ/powers/PEX + vanilla forms readback')
    return report
