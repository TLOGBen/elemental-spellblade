import struct,zlib,os,collections,sys
MO2='D:/Game/Other/SKSE/MO2'; DATA='D:/Game/Other/SKSE/SkyrimSE/Data'
prof=MO2+'/profiles/normal'
mods=[l[1:].strip() for l in open(prof+'/modlist.txt',encoding='utf-8-sig') if l.startswith('+')]
# modlist top = highest priority
where={}
for m in reversed(mods):
    d=os.path.join(MO2,'mods',m)
    try:
        for f in os.listdir(d):
            if f.lower().endswith(('.esp','.esm','.esl')): where[f.lower()]=os.path.join(d,f)
    except OSError: pass
for f in os.listdir(DATA):
    if f.lower().endswith(('.esp','.esm','.esl')): where.setdefault(f.lower(),os.path.join(DATA,f))
active=['skyrim.esm','update.esm','dawnguard.esm','hearthfires.esm','dragonborn.esm']+[l[1:].strip().lower() for l in open(prof+'/plugins.txt',encoding='utf-8-sig') if l.startswith('*')]
def recs(buf,off,end):
    while off+24<=end:
        sig=buf[off:off+4]; size=struct.unpack_from('<I',buf,off+4)[0]
        if sig==b'GRUP':
            yield from recs(buf,off+24,off+size); off+=size; continue
        flags,fid=struct.unpack_from('<II',buf,off+8); data=buf[off+24:off+24+size]
        if flags&0x40000:
            try: data=zlib.decompress(data[4:])
            except Exception: data=b''
        yield sig,fid,data; off+=24+size
def subs(data):
    o=0
    while o+6<=len(data):
        s=data[o:o+4]; n=struct.unpack_from('<H',data,o+4)[0]; yield s,data[o+6:o+6+n]; o+=6+n
out=collections.OrderedDict()
for p in dict.fromkeys(active):
    path=where.get(p)
    if not path: continue
    try: d=open(path,'rb').read()
    except OSError: continue
    if d[:4]!=b'TES4': continue
    tflags=struct.unpack_from('<I',d,8)[0]; loc=bool(tflags&0x80)
    tes4=struct.unpack_from('<I',d,4)[0]
    # only scan PERK group quickly
    for sig,fid,data in recs(d,24+tes4,len(d)):
        if sig!=b'PERK': continue
        ed=full=None; cur=None; prio=None; hits=[]
        for s,v in subs(data):
            if s==b'EDID': ed=v.rstrip(b'\0').decode('utf-8','replace')
            elif s==b'FULL' and not loc: full=v.rstrip(b'\0').decode('utf-8','replace')
            elif s==b'PRKE': cur=v[0]; prio=v[2] if len(v)>2 else None
            elif s==b'DATA' and cur==2 and len(v)>=1 and v[0]==0x33: hits.append(prio)
        if hits: out[(p,ed)]=(full,sorted(set(hits)),len(hits))
by=collections.defaultdict(list)
for (p,ed),(full,pr,n) in out.items(): by[p].append((ed,full,pr,n))
for p,l in by.items():
    print(f'== {p}  ({len(l)} perks)')
    for ed,full,pr,n in l: print(f'   {ed} | {full or ""} | prio {pr} | entries {n}')
