"""Round 18 record families; no target-status migration."""
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
    rows=[]
    for e in range(1,12):
        for p in range(2):
            rows.append(dict(id=b.ID_HIT_SPELL+(e-1)*2+p,edid=f'ESSB_Hit_{b.ELEMENTS[e-1]}_'+('Power' if p else 'Normal'),e=e,p=p,s=0,band=0,ratio=1.0,existing=True))
    def add(e,p,s=0,band=0,ratio=1.0,suffix=''):
        rows.append(dict(id=VARIANT+len([x for x in rows if not x['existing']]),edid=f'ESSB_Hit_{b.ELEMENTS[e-1]}_'+suffix,e=e,p=p,s=s,band=band,ratio=ratio,existing=False))
    for p in range(2):
        pn='Power' if p else 'Normal'
        add(5,p,s=1,suffix='Sneak'+pn)
        for band in range(1,4):add(6,p,band=band,suffix=pn+f'_B{band}')
        for j,value in enumerate([3,8,13,18,23],1):add(3,p,ratio=value/13,suffix=pn+f'_R{j}')
        add(3,p,ratio=5/13,suffix=pn+'_Inc')
    return rows

def entries(b,mode='chain'):
    rows=variants(b); out=[]
    def spell(e,p,s,band,j=None,inc=False):
        return next(x for x in rows if x['e']==e and x['p']==p and x['s']==s and x['band']==band and (x['edid'].endswith('_Inc') if inc else x['edid'].endswith(f'_R{j}') if j else x['ratio']==1 and not x['edid'].endswith('_R3')))
    for e in range(1,12):
        attacks=[(False,False,None),(False,True,None),(True,False,False),(True,True,True)]
        if e==5:attacks=[(False,p,s) for p in (False,True) for s in (False,True)]+[(True,False,False),(True,True,True)]
        for ranged,power,sneak in attacks:
            for band in range(4 if e==6 else 1):
                js=list(range(5,0,-1)) if e==3 and mode=='chain' else list(range(1,6)) if e==3 else [None]
                for j in js:
                    cond=[(0,b.gv_eq(b.own(b.ID_GLOB['ESSB_Enabled']),1)),(0,b.gv_eq(b.own(b.ID_GLOB['ESSB_FormActive']),1)),(0,b.gv_eq(b.own(b.ID_GLOB['ESSB_CurrentElement']),e))]
                    if ranged:
                        cond += [(0,b.ctda(1,7,597,1)),(0,b.ctda(0,12,597,1))]
                    else:
                        cond += [(0,b.ctda(0x20,7,597,1)),(0,b.ctda(0x20,12,597,1)),(0,b.ctda(0,int(power),673))]
                    if sneak is not None:cond.append((0,b.ctda(0,int(sneak),286)))
                    if e==6:
                        lower=[.85,.5,.2,0][band];upper=[None,.85,.5,.2][band]
                        cond.append((0,b.ctda(0x60,lower,640,24)))
                        if upper is not None:cond.append((0,b.ctda(0x80,upper,640,24)))
                    if j and ((mode=='chain' and j>1) or (mode=='additive' and j>1)):
                        chance=(1/j if mode=='chain' else .5)*100
                        cond.append((0,b.ctda(0x80,chance,77)))
                    cond += [(2,b.ctda(0,0,f)) for f in (453,700,46,569)]
                    v=spell(e,int(power),int(bool(sneak)) if e==5 else 0,band,j if mode=='chain' or j==1 else None,inc=mode=='additive' and j>1)
                    out.append(dict(e=e,p=int(power),s=sneak,ranged=ranged,band=band,j=j,spell=v['id'],conditions=cond))
    return out

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


def append_variants(b,rr,add,settings):
    from tes import subs
    byid={struct.unpack_from('<I',raw,12)[0]&0xffffff:list(subs(raw[24:])) for sig,raw in rr if sig=='SPEL'}
    for v in variants(b):
        if v['existing']:continue
        ss=byid[b.ID_HIT_SPELL+(v['e']-1)*2+v['p']]
        magnitude=(13 if v['e']==3 else sum(settings['element_damage'][b.ELEMENTS[v['e']-1]])/2)*(1.5 if v['p'] else 1)*v['ratio']
        if v['s']:magnitude*=3
        if v['e']==6:magnitude*=[1.25,1.1,.85,.6][v['band']]
        effect_index=-1;out=[]
        for k,value in ss:
            if k=='EDID':continue
            if k=='EFID':effect_index+=1
            if k=='EFIT' and effect_index==0:value=struct.pack('<fII',magnitude,0,0)
            if k=='EFIT' and effect_index==1 and v['e']==6:value=struct.pack('<fII',magnitude*.15,0,0)
            if k=='EFIT' and effect_index==1 and v['e']==3:value=struct.pack('<fII',magnitude*.5*settings['mult_drain'],0,0)
            out.append((k,value))
        add('SPEL',v['id'],v['edid'],out)

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
