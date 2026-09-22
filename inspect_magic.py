import collections,re,struct
from tes import *

rr,inputs,order,roots=effective({'SPEL','MGEF','BOOK','PERK','FLST','KYWD','GLOB'})
quest_records,_=read_plugin(Path(inputs['Phenderix Elements.esp']['path']),{'QUST'})
rr.update({r.key:r for r in quest_records})
books=collections.defaultdict(list)
bad_refs=[]
for r in rr.values():
    d=r.d
    if r.sig=='BOOK' and len(d.get('DATA',b''))>=8 and d['DATA'][0]&4:
        try: books[r.ref(u32(d['DATA'],4))].append(r.key)
        except ValueError as error: bad_refs.append({'book':r.key,'error':str(error)})
out=[]
for key,tomes in books.items():
    r=rr.get(key)
    if not r or r.sig!='SPEL': continue
    effects=[]
    for ekey in r.refs('EFID'):
        e=rr.get(ekey)
        if not e: continue
        d=e.d.get('DATA',b'')
        effects.append({'key':ekey,'edid':e.edid,'name':e.name,'school':struct.unpack_from('<i',d,12)[0] if len(d)>=16 else None,
            'resist':struct.unpack_from('<i',d,16)[0] if len(d)>=20 else None,'skill':u32(d,40) if len(d)>44 else None,
            'archetype':u32(d,64) if len(d)>68 else None,'av':u32(d,68) if len(d)>72 else None,
            'flags':u32(d) if d else None,'kw':[rr[k].edid if k in rr else k for k in e.keywords], 'vmad': 'VMAD' in e.d})
    out.append({'key':key,'edid':r.edid,'name':r.name,'winner':r.source,'type':u32(r.d['SPIT'],8),'kw':[rr[k].edid if k in rr else k for k in r.keywords],'effects':effects,'tomes':tomes})
dump(WORK/'build/learnable-inventory.json',out)
dump(WORK/'build/invalid-book-references.json',bad_refs)
dump(WORK/'build/phenderix-records.json',[{'key':r.key,'sig':r.sig,'edid':r.edid,'ss':[(k,v.hex()) for k,v in r.ss]} for r in rr.values() if r.key.startswith('phenderix elements.esp|')])
dump(WORK/'build/perk-inspection.json',[{'key':r.key,'edid':r.edid,'name':r.name,'ss':[(k,v.hex()) for k,v in r.ss]} for r in rr.values() if r.sig=='PERK' and (r.edid.startswith('ORD_Des') or r.edid.startswith('ORD_Alt_AlterationMastery') or r.edid.startswith('ORD_Con_ConjurationMastery') or r.edid.startswith('ORD_Res_RestorationMastery') or r.edid in ('DestructionNovice00','DestructionApprentice25','AugmentedFlames','AugmentedFrost','AugmentedShock'))])
print('Spell-tome spells',len(out),'spell type',dict(collections.Counter(r['type'] for r in out)))
print('By plugin',dict(collections.Counter(r['key'].split('|')[0] for r in out)))
print('Learnable spells with script effects',sum(any(e['vmad'] for e in r['effects']) for r in out))
