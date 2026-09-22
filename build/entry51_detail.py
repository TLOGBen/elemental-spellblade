"""Resolve final records, typed links and VMAD; decompile local active Papyrus only."""
from entry51_audit import *
import mmap,zlib,runpy
def vmad(r):
 data=r.d.get('VMAD',b'');out=[]
 if not data:return out
 p=0
 def get(fmt):
  nonlocal p
  v=struct.unpack_from('<'+fmt,data,p);p+=struct.calcsize('<'+fmt);return v[0] if len(v)==1 else v
 def string():
  nonlocal p
  n=get('H');v=data[p:p+n];p+=n;return v.decode('utf-8',errors='replace')
 def obj(fmt):
  if fmt==2: unused,alias,fid=get('HhI')
  else: fid,alias,unused=get('IhH')
  try:key=r.ref(fid)
  except ValueError:key='INVALID:'+hex(fid)
  return {'form':key,'alias':alias}
 def val(t,fmt):
  if t>=11:return [val(t-10,fmt) for _ in range(get('I'))]
  if t==1:return obj(fmt)
  if t==2:return string()
  return get({3:'i',4:'f',5:'B'}[t])
 def scripts(fmt,n):
  for _ in range(n):
   row={'name':string(),'status':get('B'),'props':{}}
   for _ in range(get('H')):
    name=string();t,status=get('BB');row['props'][name]=val(t,fmt)
   out.append(row)
 try:
  version,fmt,n=get('3H');scripts(fmt,n)
  if r.sig=='QUST' and p<len(data):
   get('B');n=get('H');string()
   for _ in range(n):get('HhIB');string();string()
   for _ in range(get('H')):
    alias=obj(fmt);av,af,an=get('3H');before=len(out);scripts(af,an)
    for row in out[before:]:row['alias_owner']=alias
  if p<len(data) and r.sig=='QUST':out.append({'error':'unparsed QUST VMAD tail','offset':p})
 except Exception as e:out.append({'error':str(e),'offset':p})
 return out
def bsa_members(path):
 # mmap skips textures/meshes payload; supports SSE LZ4 and LE zlib.
 from fix5_read_bsa import lz4_frame
 with path.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as d:
  magic,ver,offset,flags,nfolders,nfiles,_,_,_=struct.unpack_from('<4s8I',d)
  assert magic==b'BSA\0' and ver in (103,104,105)
  p=offset;counts=[]
  for _ in range(nfolders):counts.append(u32(d,p+8));p+=24 if ver==105 else 16
  ent=[]
  for count in counts:
   n=d[p];p+=1;folder=d[p:p+n].rstrip(b'\0').decode('utf-8',errors='replace');p+=n
   for _ in range(count):_,size,start=struct.unpack_from('<QII',d,p);p+=16;ent.append((folder,size,start))
  for folder,size,start in ent:
   end=d.find(b'\0',p);name=d[p:end].decode('utf-8',errors='replace');p=end+1
   if not name.lower().endswith(('.pex','.strings','.dlstrings','.ilstrings')):continue
   raw=d[start:start+(size&0x3fffffff)]
   if flags&0x100:raw=raw[1+raw[0]:]
   if bool(flags&4)^bool(size&0x40000000):
    expected=u32(raw);raw=lz4_frame(raw[4:]) if ver==105 else zlib.decompress(raw[4:]);assert len(raw)==expected
   yield (folder+'/'+name).replace('\\','/'),raw
def main():
 records,history,meta=pickle.loads((W/'build/entry51-records.pickle').read_bytes())
 refs=collections.defaultdict(list);vms={};errs=[]
 def link(r,fid,why):
  if not fid:return
  try:key=r.ref(fid)
  except ValueError:errs.append([r.key,why,hex(fid)]);return
  refs[key].append({'from':r.key,'field':why})
 for r in records.values():
  for k,v in r.ss:
   if (k in ('PNAM',) and r.sig in ('AVIF','PERK')) or (k in ('EFID','SPLO','LNAM','RNAM','ETYP','EITM','TNAM') and len(v)==4):link(r,u32(v),k)
   if k=='PRKR' and r.sig=='NPC_':link(r,u32(v),'NPC perk')
   if k=='DATA' and r.sig=='MGEF' and len(v)>=140:
    link(r,u32(v,136),'MGEF perk to apply');link(r,u32(v,128),'MGEF equip ability')
   if k=='DATA' and r.sig=='BOOK' and len(v)>=12 and v[0]&4:link(r,u32(v,8),'BOOK taught spell')
  if 'VMAD' in r.d:
   rows=vmad(r);vms[r.key]=rows
   for row in rows:
    for prop,value in row.get('props',{}).items():
     for v in value if isinstance(value,list) else [value]:
      if isinstance(v,dict) and v.get('form'):refs[v['form']].append({'from':r.key,'field':'VMAD '+row['name']+'.'+prop,'alias':v['alias']})
 dump('entry51-links.json',dict(refs));dump('entry51-vmad.json',vms);dump('entry51-link-errors.json',errs)
 inventory=json.loads((W/'build/entry51-inventory.json').read_text(encoding='utf8'));inputs=json.loads((W/'build/entry51-inputs.json').read_text(encoding='utf8'))
 order={Path(n).stem.lower():i for i,n in enumerate(inputs['order'])};archives=[]
 for row in inventory:
  if not row['enabled'] or row['suffix']!='.bsa':continue
  stem=Path(row['path']).stem.lower();base=stem.split(' - ')[0]
  if base in order:archives.append((order[base],row))
 archives.sort(key=lambda x:x[0]);scripts={};strings={};archiveerrors=[]
 for i,(_,row) in enumerate(archives):
  try:
   for name,data in bsa_members(Path(row['path'])):
    if name.lower().endswith('.pex'):scripts[Path(name).name.lower()]=(row['path']+'::'+name,data)
    else:strings[Path(name).name.lower()]=(row['path']+'::'+name,data)
  except Exception as e:archiveerrors.append([row['path'],str(e)])
  if i%100==0:print('archives',i,len(archives),'scripts',len(scripts),flush=True)
 for name,(_,path) in inputs['loose_scripts'].items():scripts[name]=(path,Path(path).read_bytes())
 from fix5_read_bsa import Pex
 decompiled={};addcalls=[];parseerrors=[]
 vmnames={s['name'].lower()+'.pex' for rows in vms.values() for s in rows if 'name' in s}
 for name,(path,data) in scripts.items():
  if b'addperk' not in data.lower() and name not in vmnames:continue
  try:tree=Pex(data).read()
  except Exception as e:parseerrors.append([name,path,str(e)]);continue
  decompiled[name]={'path':path,'tree':tree}
  for obj in tree['objects']:
   for state,fs in obj['states'].items():
    for fn,body in fs.items():
     for i,(op,args) in enumerate(body['code']):
      if op==23 and str(args[0]).lower()=='addperk':addcalls.append({'script':name,'path':path,'state':state,'function':fn,'index':i,'instruction':args,'code':body['code']})
 dump('entry51-addperk-bytecode.json',addcalls);dump('entry51-script-errors.json',{'archives':archiveerrors,'pex':parseerrors,'scripts_indexed':len(scripts),'archives_indexed':len(archives),'missing_vmad_scripts':sorted(vmnames-scripts.keys())})
 with (W/'build/entry51-scripts.pickle').open('wb') as f:pickle.dump((decompiled,strings),f)
 print('decompiled',len(decompiled),'AddPerk calls',len(addcalls),'errors',len(parseerrors),len(archiveerrors),flush=True)
if __name__=='__main__':main()
