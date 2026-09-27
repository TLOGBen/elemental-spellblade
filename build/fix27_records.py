"""Round 27 (G13, the visuals) records.

  ESSB_WeaponGlow                  the MCM switch 「形態光圈」 (default 1; round 27b: the ring, the EditorID kept). Every ring
                                   effect of the form abilities is conditioned on it.
  ESSB_FormRingEffect_<X>_<N>      round 27b (the user's decision 2026-09-27): the form's feedback is a ring of light at your
                                   feet in the element's colour, on while the form is open, one of four by ESSB_SyncStage 0..3
                                   (mutually exclusive), nothing on the weapon. The vanilla pattern: the master spells'
                                   FX*BodyHolder effects (archetype 1, a constant self effect, flags 0x9200, Hit Effect Art =
                                   the ritual *CastBodyFX ring). RING_ART picks the Skyrim.esm art object per element and stage.
  (retired, round 27b)             ESSB_WeaponGlowEnchEffect_<X>_<S> and ESSB_WeaponGlowEnch_<X>_<S> stay in the ESP (FormIDs
                                   append-only) but nothing uses them; round 18's ESSB_SyncWeaponEffect_<X>_<S> are inert.
  ESSB_WeaponGlowEnchEffect_<X>_<S> the weapon enchantment's effect: no gameplay (a script archetype without a script,
                                   magnitude 0), its Enchant Shader is the element's glow at that brightness
                                   (ESSB_WeaponShader_<X>_<S>, round 18's three alpha tiers). v0.4 2.11: 「附魔武器的樣子」.
  ESSB_WeaponGlowEnch_<X>_<S>      the enchantment (ENCH) the form ability's glow effect puts on your weapon.
                                   build/fix18_records.py turns ESSB_SyncWeaponEffect_<X>_<S> into an Enhance Weapon
                                   effect (archetype 39) with this ENCH as its associated item -- the engine's own way to
                                   give a weapon an enchantment's look from a self effect (vanilla VoiceElementalFury,
                                   0x02C56F, with VoiceEnchElementalFury 0x02C594); it follows weapon swaps
                                   (EnhanceWeaponEffect listens to ActorInventoryEvent).
  ESSB_MarkFlashEffect_<X>, ESSB_MarkFlash_<X>
                                   v0.4 2.12「開印：目標身上一次該元素的 Art Object 閃現」: a 1 s visual-only effect with the
                                   element's ZZArt as its Hit Effect Art and the Charge sound; the DLL casts it on an open
                                   (the mark effect keeps only its persistent edge light).

IDs 0x005D00-0x005DFF (after round 26's 0x005C00-0x005CFF). Append-only.
"""
import struct

BASE = 0x5D00
WEAPON_GLOW_GLOBAL = 'ESSB_WeaponGlow'
STAGES = ['Dim', 'Mid', 'Bright']

_ids = {'WeaponGlow.glob': BASE}
ENCH_EFFECT = BASE + 0x10      # 33: element × stage
ENCH = BASE + 0x40             # 33
FLASH_EFFECT = BASE + 0x70     # 11
FLASH_SPELL = BASE + 0x80      # 11
RING_EFFECT = BASE + 0x90      # 44: element × sync stage 0..3 (round 27b)
SWITCH_TICKET = BASE + 0xC0    # round 27b (review B N8): the form switches' ticket and turn (ESSBController.OnESSBSwitch)
SWITCH_TURN = BASE + 0xC1
RING_ARTO = BASE + 0xC2        # 11: round 27d, our own art objects on vanilla ground models (the ring)
LAST = RING_ARTO + 10
assert LAST <= 0x5DFF, hex(LAST)

# ENCH ENIT (36 bytes, vanilla VoiceEnchElementalFury): cost 0, flags 0, cast type 1 (fire and forget), charge 0,
# delivery 1 (contact), enchantment type 6 (Enchantment), charge time 0, no base enchantment, no worn restriction.
ENIT = struct.pack('<iIIiIIfII', 0, 0, 1, 0, 1, 6, 0.0, 0, 0)
# The glow enchantment's effect: 0x8000 hide in UI, 0x800 no area, 0x400 no magnitude, 0x200 no duration, 0x10 no hit
# event -- it does nothing where the weapon lands (a script archetype with no script).
ENCH_EFFECT_FLAGS = 0x00008E10
# The open flash: hidden, no magnitude / area / hit event, FX persist (the art lasts the effect's 1 s); NOT hostile (a
# flash starts no fight and no crime).
FLASH_FLAGS = 0x00009C10
FLASH_SECONDS = 1


def glow_id():
    return _ids['WeaponGlow.glob']


def ench_effect_id(element_index, stage):
    return ENCH_EFFECT + element_index * 3 + stage


def ench_id(element_index, stage):
    return ENCH + element_index * 3 + stage


# Round 27d (the in-game report: no ring at all on 0.27.1): round 27b used the master spells' *CastBodyFX art objects --
# casting art for the ritual charge (hand / body nodes while the caster charges), not a ground ring, and nothing showed.
# The ring is now our own art object (a Magic Hit Effect ARTO, DNAM 1) on a vanilla GROUND model: the rune spells'
# projectile glyphs (Skyrim.esm fire / frost / lightning; Dragonborn's poison / frenzy / ash runes -- their meshes are in
# the SE base archives, no master needed) and the restoration circles (Circle of Protection, Guardian Circle). The
# model's origin is the ground plane, so on the actor it lies at the feet. Earth, wind, water and astral have no vanilla
# rune of their colour: they reuse the nearest circle (documented in build/fix27_visuals.py INVENTORY).
RING_MODELS = {
    'Fire': 'Magic\\RuneFireProjectile01.nif',
    'Frost': 'Magic\\RuneFrostProjectile01.nif',
    'Lightning': 'Magic\\RuneLightningProjectile01.nif',
    'Earth': 'DLC02\\Effects\\RuneAshProjectile.nif',
    'Wind': 'Magic\\HealingHazard.nif',
    'Blood': 'DLC02\\Effects\\RuneFrenzyProjectile.nif',
    'Divine': 'Magic\\TurnUndeadHazard.nif',
    'Poison': 'DLC02\\Effects\\RunePoisonProjectile.nif',
    'Water': 'Magic\\HealingHazard.nif',
    'Darkness': 'DLC02\\Effects\\RuneAshProjectile.nif',
    'Astral': 'Magic\\TurnUndeadHazard.nif',
}
ARTO_MAGIC_HIT = 1
RING_STAGES = 4
RING_FLAGS = 0x00009200   # vanilla FX*BodyHolder: 0x8000 hide in UI, 0x1000 FX persist, 0x200 no duration


def ring_effect_id(element_index, stage):
    return RING_EFFECT + element_index * RING_STAGES + stage


def ring_arto_id(element_index):
    return RING_ARTO + element_index


def ring_art(name, stage):
    """The local id of the ring's art object (ours) for an element and stage (one art for all four stages)."""
    return ring_arto_id(ELEMENTS.index(name))


def flash_effect_id(element_index):
    return FLASH_EFFECT + element_index


def flash_spell_id(element_index):
    return FLASH_SPELL + element_index


def add_records(b, add, fx_ph):
    """b: build_v03; fx_ph(name, ix): the Phenderix record of an element (ZZArt_<X>, ZZSoundDescriptor_Charge_<X>)."""
    I, Z, own = b.I, b.Z, b.own
    assert list(b.ELEMENTS) == ELEMENTS, b.ELEMENTS
    import fix18_records as hit18
    add('GLOB', glow_id(), WEAPON_GLOW_GLOBAL, [('FNAM', b's'), ('FLTV', b.F(1))])
    add('GLOB', SWITCH_TICKET, 'ESSB_FormSwitchTicket', [('FNAM', b'f'), ('FLTV', b.F(0))])
    add('GLOB', SWITCH_TURN, 'ESSB_FormSwitchTurn', [('FNAM', b'f'), ('FLTV', b.F(0))])
    for ix, name in enumerate(b.ELEMENTS):
        for stage, tier in enumerate(STAGES):
            shader = own(hit18.WEAPON_SHADER + ix * 3 + stage)
            add('MGEF', ench_effect_id(ix, stage), f'ESSB_WeaponGlowEnchEffect_{name}_{tier}', [
                ('FULL', Z(f'{b.ZH[ix]}武器光')),
                ('DATA', b.mgef_data(ENCH_EFFECT_FLAGS, 1, casting=1, delivery=1, enchant_shader=shader)),
            ])
            add('ENCH', ench_id(ix, stage), f'ESSB_WeaponGlowEnch_{name}_{tier}', [
                ('OBND', bytes(12)), ('FULL', Z(f'{b.ZH[ix]}武器光')),
                ('ENIT', ENIT),
                ('EFID', I(own(ench_effect_id(ix, stage)))), ('EFIT', struct.pack('<fII', 0.0, 0, 0)),
            ])
        add('ARTO', ring_arto_id(ix), f'ESSB_FormRingArt_{name}', [
            ('OBND', bytes(12)), ('MODL', Z(RING_MODELS[name])), ('DNAM', I(ARTO_MAGIC_HIT)),
        ])
        for stage in range(RING_STAGES):
            add('MGEF', ring_effect_id(ix, stage), f'ESSB_FormRingEffect_{name}_{stage}', [
                ('FULL', Z(f'{b.ZH[ix]}形態光圈')),
                ('DATA', b.mgef_data(RING_FLAGS, 1, casting=0, delivery=0, hit_effect_art=own(ring_art(name, stage)))),
            ])
        add('MGEF', flash_effect_id(ix), f'ESSB_MarkFlashEffect_{name}', [
            ('FULL', Z(f'{b.ZH[ix]}開印')),
            ('DATA', b.mgef_data(FLASH_FLAGS, 1, casting=1, delivery=1, hit_effect_art=fx_ph('ZZArt', ix))),
            ('SNDD', b.sndd([(b.SND_CHARGE, fx_ph('ZZSoundDescriptor_Charge', ix))])),
        ])
        add('SPEL', flash_spell_id(ix), f'ESSB_MarkFlash_{name}', [
            ('OBND', bytes(12)), ('FULL', Z(f'{b.ZH[ix]}開印')),
            ('ETYP', I(b.ref('Skyrim.esm', 0x13F45))), ('DESC', Z('')),
            ('SPIT', b.spit(0, 1, 1)),
            ('EFID', I(own(flash_effect_id(ix)))), ('EFIT', struct.pack('<fII', 0.0, 0, FLASH_SECONDS)),
        ])


ELEMENTS = ['Fire', 'Frost', 'Lightning', 'Earth', 'Wind', 'Blood', 'Divine', 'Poison', 'Water', 'Darkness', 'Astral']


def contact_edids():
    """The open flashes are contact casts on the target (build_v03 validate_delivery)."""
    return {f'ESSB_MarkFlash_{name}' for name in ELEMENTS}


def new_edids():
    names = {WEAPON_GLOW_GLOBAL, 'ESSB_FormSwitchTicket', 'ESSB_FormSwitchTurn'}
    for name in ELEMENTS:
        names |= {f'ESSB_WeaponGlowEnchEffect_{name}_{t}' for t in STAGES}
        names |= {f'ESSB_WeaponGlowEnch_{name}_{t}' for t in STAGES}
        names |= {f'ESSB_MarkFlashEffect_{name}', f'ESSB_MarkFlash_{name}'}
        names |= {f'ESSB_FormRingEffect_{name}_{s}' for s in range(RING_STAGES)}
        names.add(f'ESSB_FormRingArt_{name}')
    return names


# ---------------------------------------------------------------- G14: the spells the DLL casts
# SPIT flags (vendor/wbDefinitionsTES5.pas; CommonLib SpellItem::SpellFlag): 0x00200000 No Absorb/Reflect (kNoAbsorb),
# 0x00100000 Ignore Resistance (kIgnoreResistance).
NO_ABSORB = 0x00200000
IGNORE_RESIST = 0x00100000


def dll_spell_flags(b):
    """(every SPEL local id the DLL casts, the pure-marker ones among them): the proc spells, the cast spells, the status
    layer's marks / reactions / kinds / domains / timed utilities / DoTs, the open flashes."""
    import fix19_native as n
    ids, markers = set(), set()
    ids |= {row['id'] for row in n.proc_rows(b)}
    ids |= {row['local_id'] for row in n.spells(b).values()}
    s = n.status_ids(b)
    for row in s['marks']:
        ids.add(row['spell'])
        markers.add(row['spell'])
    ids |= {row['spell'] for row in s['react']}
    for row in s['kinds']:
        ids.add(row['spell'])
        markers.add(row['spell'])
    for row in s['domains']:
        ids.add(row['hazard_spell'])
        ids |= set(row['spawn'])
    for row in s['timed']:
        ids |= set(row['spells'])
    for row in s['dots'].values():
        ids |= set(row['spells'])
    ids |= {flash_spell_id(ix) for ix in range(len(ELEMENTS))}
    return ids, markers


def delivered_to_others(ss):
    """A spell whose SPIT delivery is contact (1) or aimed (2): it lands on someone else."""
    spit = next((v for k, v in ss if k == 'SPIT'), None)
    return spit is not None and struct.unpack_from('<I', spit, 20)[0] in (1, 2)


def flag_spit(ss, marker):
    """The subrecords of one spell with No Absorb/Reflect set (and Ignore Resistance for a one-effect marker)."""
    efids = sum(1 for k, _ in ss if k == 'EFID')
    out = []
    for k, v in ss:
        if k == 'SPIT':
            data = bytearray(v)
            flags = struct.unpack_from('<I', data, 4)[0] | NO_ABSORB | (IGNORE_RESIST if marker and efids == 1 else 0)
            struct.pack_into('<I', data, 4, flags)
            v = bytes(data)
        out.append((k, v))
    return out
