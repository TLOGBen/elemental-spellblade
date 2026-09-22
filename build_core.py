"""Build an independent ESL-flagged core, with stable local FormIDs."""
import collections,json,re,struct
from tes import *

PLUGIN='Elements Spellblade.esp'
OUT=WORK/'package/Elements Spellblade'
MASTERS=['Skyrim.esm','Phenderix Elements.esp']
ELEMENTS=['fire','frost','lightning','earth','wind','blood','divine','poison','water','darkness','astral']
ZH=['火焰','冰霜','雷電','大地','風','鮮血','神聖','毒素','水','黑暗','星界']
SCHOOLS=[20,20,20,18,18,22,22,22,18,19,20]
ACTIVE=[0x096072,0x096073,0x096074,0x096075,0x096076,0x096077,0x096078,0x096079,0x09607A,0x0A02AC,0x2C322D]
ELEM_KW=[('Skyrim.esm',0x1CEAD),('Skyrim.esm',0x1CEAE),('Skyrim.esm',0x1CEAF),('Phenderix Elements.esp',0x123EC8),('Phenderix Elements.esp',0x160AFE),('Phenderix Elements.esp',0x1568F6),('Phenderix Elements.esp',0x114BB4),('Phenderix Elements.esp',0x160B00),('Phenderix Elements.esp',0x160AFF),('Phenderix Elements.esp',0x160AFD),('Phenderix Elements.esp',0x2CD433)]
I=lambda x:struct.pack('<I',x)
F=lambda x:struct.pack('<f',x)
Z=lambda s:s.encode('utf-8')+b'\0'
def ref(plugin,fid): return (MASTERS.index(plugin)<<24)|fid
def own(fid):return (len(MASTERS)<<24)|fid
def vstr(s):
    b=s.encode('utf-8');return struct.pack('<H',len(b))+b
def obj(fid,alias=-1):return struct.pack('<HhI',0,alias,fid)
def script(name,props):
    body=vstr(name)+b'\0'+struct.pack('<H',len(props))
    for prop,(typ,value) in props.items():
        body+=vstr(prop)+bytes([typ,1])
        if typ==1:body+=obj(value)
        elif typ==11:body+=I(len(value))+b''.join(obj(x) for x in value)
        else:raise ValueError(typ)
    return body
def vmad(name,props):return struct.pack('<3H',5,2,1)+script(name,props)
def record(sig,fid,ss,flags=0):
    raw=b''.join(sub(k,v) for k,v in ss)
    return struct.pack('<4sIIIIHH',sig.encode(),len(raw),flags,fid,0,44,0)+raw
def cond(function,param=0,value=1.0,operator=0):
    return bytes([operator,0,0,0])+F(value)+struct.pack('<H2xIIIIi',function,param,0,0,0,-1)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    settings=json.loads((WORK/'settings.json').read_text(encoding='utf-8'))
    # The active perk overhaul checks the original casting-perk identity, not just school.
    base,_=read_plugin(ROOT/'SkyrimSE/Data/Skyrim.esm',{'PERK'})
    byedid={r.edid:r for r in base}
    school_names={18:'Alteration',19:'Conjuration',20:'Destruction',21:'Illusion',22:'Restoration'}
    casting_perks={school:int(byedid[name+'Novice00'].key.split('|')[1],16) for school,name in school_names.items()}
    rr=[];manifest={}
    def add(sig,fid,edid,ss):
        rr.append((sig,record(sig,own(fid),[('EDID',Z(edid))]+ss)))
        manifest[edid]={'id':f'{fid:06X}','type':sig}
    add('KYWD',0x801,'ESSBProc',[])
    add('GLOB',0x802,'ESSBEnabled',[('FNAM',b's'),('FLTV',F(int(settings['melee_enabled'])))])
    add('GLOB',0x803,'ESSBDebugEnabled',[('FNAM',b's'),('FLTV',F(int(settings['debug_logging'])))])
    for i,e in enumerate(ELEMENTS):
        data=bytearray(152)
        struct.pack_into('<I',data,0,0x00208A15) # hostile/detrimental/no hit event/no duration/no area/hidden/power magnitude
        struct.pack_into('<f',data,4,1.0)
        struct.pack_into('<i',data,12,SCHOOLS[i])
        struct.pack_into('<i',data,16,{0:41,1:43,2:42,7:40}.get(i,44))
        struct.pack_into('<I',data,64,0) # Value Modifier
        struct.pack_into('<I',data,68,24) # Health
        struct.pack_into('<I',data,80,1) # Fire and Forget
        struct.pack_into('<I',data,84,3) # Target Actor, no projectile
        struct.pack_into('<i',data,88,-1)
        struct.pack_into('<I',data,140,2) # silent casting sound level
        kws=[ref(*ELEM_KW[i]),own(0x801)]
        add('MGEF',0x880+i,'ESSBHitEffect'+e.title(),[('FULL',Z(ZH[i]+'附傷')),('KSIZ',I(len(kws))),('KWDA',b''.join(I(x) for x in kws)),('DATA',bytes(data)),('DNAM',Z('命中時造成 <mag> 點'+ZH[i]+'傷害。'))])
        for power in (0,1):
            magnitude=settings['power_damage'] if power else settings['normal_damage']
            spit=struct.pack('<IIIfIIffI',0,1,0,0.0,1,3,0.0,0.0,ref('Skyrim.esm',casting_perks[SCHOOLS[i]]))
            add('SPEL',0x900+i*2+power,'ESSBHit'+e.title()+('Power' if power else 'Normal'),[
                ('OBND',bytes(12)),('FULL',Z('元素魔戰士：'+ZH[i]+'附傷')),('KSIZ',I(1)),('KWDA',I(own(0x801))),
                ('ETYP',I(ref('Skyrim.esm',0x13F45))),('DESC',Z('')),
                ('SPIT',spit),('EFID',I(own(0x880+i))),('EFIT',struct.pack('<fII',magnitude,0,0))])
    menu=[('DESC',Z('近戰附傷：%.0f（1＝開啟）\n命中紀錄：%.0f\n\n近戰依目前元素形態附傷；左右手及重擊各依實際命中計算。數值設定請修改擴充工具的 settings.json 後重建。')),('INAM',I(0)),('QNAM',I(0)),('DNAM',I(1))]
    for label in ['切換近戰附傷','切換命中紀錄','關閉']:menu.append(('ITXT',Z(label)))
    add('MESG',0x805,'ESSBSettingsMenu',menu)
    data=bytearray(152);struct.pack_into('<I',data,0,0x8E00);struct.pack_into('<i',data,12,-1);struct.pack_into('<i',data,16,-1)
    struct.pack_into('<I',data,64,1);struct.pack_into('<i',data,68,-1);struct.pack_into('<I',data,80,1);struct.pack_into('<i',data,88,-1)
    add('MGEF',0x806,'ESSBSettingsEffect',[('VMAD',vmad('ESSBSettingsEffect',{'SettingsMenu':(1,own(0x805)),'Enabled':(1,own(0x802)),'DebugEnabled':(1,own(0x803))})),('FULL',Z('元素魔戰士設定')),('DATA',bytes(data))])
    add('SPEL',0x804,'ESSBSettingsPower',[('OBND',bytes(12)),('FULL',Z('元素魔戰士：設定')),('ETYP',I(ref('Skyrim.esm',0x25BEE))),('DESC',Z('開關近戰附傷及切換診斷紀錄。')),('SPIT',struct.pack('<IIIfIIffI',0,1,3,0.0,1,0,0.0,0.0,0)),('EFID',I(own(0x806))),('EFIT',struct.pack('<fII',0.0,0,1))])
    props={'Enabled':(1,own(0x802)),'DebugEnabled':(1,own(0x803)),'AnyFormActive':(1,ref('Phenderix Elements.esp',0x08BE5D)),
        'ActiveForms':(11,[ref('Phenderix Elements.esp',v) for v in ACTIVE]),'NormalSpells':(11,[own(0x900+i*2) for i in range(11)]),
        'PowerSpells':(11,[own(0x901+i*2) for i in range(11)]),'SettingsPower':(1,own(0x804))}
    quest_vmad=struct.pack('<3H',5,2,0)+b'\x02\x00\x00\x00\x00'+struct.pack('<H',1)+obj(own(0x800),0)+struct.pack('<3H',5,2,1)+script('ESSBPlayerAlias',props)
    add('QUST',0x800,'ESSBStartupQuest',[('VMAD',quest_vmad),('DNAM',struct.pack('<HBBII',0x11,0,255,0,0)),('NEXT',b''),('ANAM',I(1)),('ALST',I(0)),('ALID',Z('Player')),('FNAM',I(0)),('ALFR',I(ref('Skyrim.esm',0x14))),('VTCK',I(0)),('ALED',b'')])
    groups=collections.defaultdict(list)
    for sig,raw in rr:groups[sig].append(raw)
    header=[('HEDR',struct.pack('<fII',1.7,len(rr)+len(groups),0xA00)),('CNAM',Z('Local Elements integration')),('SNAM',Z('Player melee elemental bonus damage. No spell catalogue or original script overrides.'))]
    for master in MASTERS:header.extend([('MAST',Z(master)),('DATA',bytes(8))])
    body=record('TES4',0,header,0x200)
    for sig,records in groups.items():
        payload=b''.join(records);body+=struct.pack('<4sI4sIHHHH',b'GRUP',24+len(payload),sig.encode(),0,0,0,0,0)+payload
    (OUT/PLUGIN).write_bytes(body)
    (OUT/'SEQ').mkdir(exist_ok=True);(OUT/'SEQ/Elements Spellblade.seq').write_bytes(I(own(0x800)))
    dump(WORK/'build/core-formids.json',manifest)
    check,_=read_plugin(OUT/PLUGIN)
    assert len(check)==len(rr) and len({r.key for r in check})==len(rr)
    print('Core:',len(rr),'records;',len(body),'bytes;',len(groups),'groups')

if __name__=='__main__':main()
