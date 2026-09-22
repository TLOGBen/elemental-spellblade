import sys,json,struct
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path.cwd()))
from tes import ROOT,read_plugin
paths=[ROOT/'SkyrimSE/Data/Skyrim.esm']
for pattern in ['**/Ordinator - Perks of Skyrim.esp','**/Phenderix Elements.esp']:paths+=list((ROOT/'MO2/mods').glob(pattern))[:1]
rows=[]
for p in paths:
 rr,_=read_plugin(p,{'PERK'})
 count=0
 for r in rr:
  entries=[];entry=None;tab=None
  for k,v in r.ss:
   if k=='PRKE':entry={'header':v.hex(),'conditions':[]};tab=None
   elif entry is not None:
    if k=='DATA':entry['data']=list(v)
    elif k=='PRKC':tab=v[0]
    elif k=='CTDA':entry['conditions'].append({'tab':tab,'op':v[0],'value':struct.unpack_from('<f',v,4)[0],'fn':struct.unpack_from('<H',v,8)[0],'p1':struct.unpack_from('<I',v,12)[0],'raw':v.hex()})
    elif k=='EPFT':entry['epft']=v[0]
    elif k=='EPFD':entry['epfd']=v.hex()
    elif k=='PRKF':entries.append(entry);entry=None
  ep=[e for e in entries if e.get('data',[0])[0]==51]
  count+=len(ep)
  interesting=ep or [e for e in entries if any(c['fn']==699 or c['fn']==597 and c['value']==12 for c in e['conditions'])]
  if interesting: rows.append({'plugin':p.name,'id':r.key,'edid':r.edid,'entries':interesting})
 print(p.name,'EP51 entries',count)
Path('build/fix18-engine-evidence.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
for row in rows:
 if row['plugin']=='Skyrim.esm' or len(row['entries'])>1:
  print(row['id'],row['edid'],[(e.get('data'),e.get('epft'),e.get('epfd')) for e in row['entries']])
