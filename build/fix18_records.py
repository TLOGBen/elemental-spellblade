"""Round 18 record families (proc spell table, bonus spells, hotkeys, weapon glows); no target-status migration."""
import struct, json
HIT_PERK=0x5200
DIVINE_ARMED=0x5201
HOTKEYS=0x5202
NOTIFY=0x520D
SOUND=0x520E
KEY_ENABLE=0x520F
BONUS_EFFECT=0x5210
BONUS_SPELL=0x5220
VARIANT=0x5240
WEAPON_EFFECT=0x5280
WEAPON_SHADER=0x52B0
KEY_CODES=[79,80,81,75,76,77,71,72,73,82,83]

def variants(b):
    """The element proc spells the DLL selects from: element x normal/power (22 records at ID_HIT_SPELL).

    Round 20 (N2) removed the round-18 magnitude variants (lightning R1-R5 and _Inc, blood B1-B3, wind
    sneak): the DLL computes the magnitude per hit and casts with an override, so one spell per element
    and attack kind is enough. The round-18 entry-51 table they served lives on only in the snapshot ESP."""
    rows=[]
    for e in range(1,12):
        for p in range(2):
            rows.append(dict(id=b.ID_HIT_SPELL+(e-1)*2+p,edid=f'ESSB_Hit_{b.ELEMENTS[e-1]}_'+('Power' if p else 'Normal'),e=e,p=p,existing=True))
    return rows

def add_records(b,add,settings,casting_perks):
    I,F,Z=b.I,b.F,b.Z;own=b.own
    add('GLOB',DIVINE_ARMED,'ESSB_DivineArmed',[('FNAM',b's'),('FLTV',F(0))])
    for i,n in enumerate(b.ELEMENTS):add('GLOB',HOTKEYS+i,'ESSB_Hotkey_'+n,[('FNAM',b's'),('FLTV',F(KEY_CODES[i]))])
    for fid,n,key in [(NOTIFY,'FormNotify','form_notify'),(SOUND,'FormSound','form_sound'),(KEY_ENABLE,'HotkeysEnabled','hotkeys_enabled')]:add('GLOB',fid,'ESSB_'+n,[('FNAM',b's'),('FLTV',F(int(settings.get(key,True))))])
    for i,n in enumerate(b.ELEMENTS):
        kws=[own(b.ID_KW_PROC),own(b.ID_KW_ELEMENT+i)]+([b.ref('Skyrim.esm',b.VANILLA_ELEMENT_KEYWORD[i])] if i in b.VANILLA_ELEMENT_KEYWORD else [])
        add('MGEF',BONUS_EFFECT+i,'ESSB_HitBonusEffect_'+n,[('FULL',Z(n+' bonus')),('KSIZ',I(len(kws))),('KWDA',b''.join(I(x) for x in kws)),('DATA',b.mgef_data(b.MGEF_HIT_FLAGS,0,base_cost=1,skill=b.SCHOOLS[i],resist=b.RESISTS[i],actor_value=24,casting=1,delivery=1,skill_usage=0))])
        fx=[('EFID',I(own(BONUS_EFFECT+i))),('EFIT',struct.pack('<fII',0.,0,0))]
        if i==2:fx += [('EFID',I(own(b.util_effect_id(2)))),('EFIT',struct.pack('<fII',0.,0,0))]
        add('SPEL',BONUS_SPELL+i,'ESSB_Hit_'+n+'_Bonus',[('OBND',bytes(12)),('FULL',Z(n+' bonus')),('KSIZ',I(1)),('KWDA',I(own(b.ID_KW_PROC))),('SPIT',b.spit(0,1,1,b.ref('Skyrim.esm',casting_perks[b.SCHOOLS[i]])))]+fx)
    # Round 19: keep the stable empty perk identity; no entry-51 fallback.
    add('PERK',HIT_PERK,'ESSB_P_HitProc',[('FULL',Z('元素魔戰士：原生命中')),('DATA',b.perk_data(playable=0,hidden=1))])
    return 0


def weapon_glows(b,add,fx_records,fxe):
    I,Z=b.I,b.Z
    for i,n in enumerate(b.ELEMENTS):
        template=next(x for x in fx_records if x['fid']==fxe('weapon',i))
        for stage,scale in enumerate([.2,.5,.85]):
            shader=WEAPON_SHADER+i*3+stage
            ss=[]
            for k,v in template['ss']:
                if k=='EDID':continue
                if k=='DATA':
                    v=bytearray(v)
                    for key in ['fill_persistent_alpha','edge_persistent_alpha','fill_full_alpha','edge_full_alpha']:
                        off=b.EFSH_FLOATS[key];struct.pack_into('<f',v,off,struct.unpack_from('<f',v,off)[0]*scale)
                    # zero fades: switch has no transition
                    for key in ['fill_fade_in','fill_fade_out','edge_fade_in','edge_fade_out']:struct.pack_into('<f',v,b.EFSH_FLOATS[key],0)
                    v=bytes(v)
                ss.append((k,v))
            add('EFSH',shader,f'ESSB_WeaponShader_{n}_{stage}',ss)
            add('MGEF',WEAPON_EFFECT+i*3+stage,f'ESSB_SyncWeaponEffect_{n}_'+['Dim','Mid','Bright'][stage],[('FULL',Z(n+' weapon glow')),('DATA',b.mgef_data(b.MGEF_UTILITY_FLAGS|0x1000,1,casting=0,delivery=0,hit_shader=0,enchant_shader=b.own(shader)))])


def new_edids(b):
    names={'ESSB_P_HitProc','ESSB_DivineArmed','ESSB_FormNotify','ESSB_FormSound','ESSB_HotkeysEnabled'}
    names |= {v['edid'] for v in variants(b) if not v['existing']}
    for n in b.ELEMENTS:
        names.update(['ESSB_Hotkey_'+n,'ESSB_HitBonusEffect_'+n,'ESSB_Hit_'+n+'_Bonus'])
        names.update(f'ESSB_WeaponShader_{n}_{i}' for i in range(3))
        names.update(f'ESSB_SyncWeaponEffect_{n}_{s}' for s in ['Dim','Mid','Bright'])
    return names
