"""Small, strict TES5 record reader/writer. All identities use origin plugin + local ID."""
from __future__ import annotations
import hashlib, json, mmap, struct, zlib
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
PROFILE = ROOT / 'MO2/profiles/normal'
BASE = ['Skyrim.esm', 'Update.esm', 'Dawnguard.esm', 'HearthFires.esm', 'Dragonborn.esm']

def lines(p): return p.read_text(encoding='utf-8-sig').splitlines()
def text(b): return b.rstrip(b'\0').decode('utf-8', errors='replace')
def u32(b, off=0): return struct.unpack_from('<I', b, off)[0]
def f32(b, off=0): return struct.unpack_from('<f', b, off)[0]
def dump(p, data): p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
def identity(plugin, fid): return plugin.casefold() + f'|{fid & 0xFFFFFF:06X}'
def config_ref(key):
    plugin, fid = key.split('|')
    return f'0x{int(fid,16):X}~{plugin}'

def environment():
    mods = [s[1:] for s in lines(PROFILE/'modlist.txt') if s.startswith('+')]
    roots = [ROOT/'SkyrimSE/Data'] + [ROOT/'MO2/mods'/s for s in reversed(mods)] + [ROOT/'MO2/overwrite']
    paths = {}
    for folder in roots:
        if folder.is_dir():
            for p in folder.iterdir():
                if p.is_file() and p.suffix.lower() in ('.esp', '.esm', '.esl'):
                    paths[p.name.casefold()] = p
    active = {s[1:].casefold() for s in lines(PROFILE/'plugins.txt') if s.startswith('*')}
    active.update(s.casefold() for s in BASE)
    ccc = ROOT/'SkyrimSE/Skyrim.ccc'
    if ccc.exists(): active.update(s.casefold() for s in lines(ccc) if s.strip())
    order = [s for s in lines(PROFILE/'loadorder.txt') if s.casefold() in active and s.casefold() in paths]
    missing = active - {s.casefold() for s in order} - (active - paths.keys())
    if missing: raise ValueError(f'Enabled plugins absent from loadorder: {missing}')
    return order, paths, roots

def subs(raw):
    p = 0; extended = None
    while p < len(raw):
        if p+6 > len(raw): raise ValueError('subrecord header overflow')
        sig, n = struct.unpack_from('<4sH', raw, p); p += 6
        if sig == b'XXXX':
            if n != 4: raise ValueError('bad XXXX')
            extended = u32(raw,p); p += 4; continue
        if extended is not None: n, extended = extended, None
        if p+n > len(raw): raise ValueError('subrecord payload overflow')
        yield sig.decode('ascii'), raw[p:p+n]
        p += n
    if extended is not None: raise ValueError('dangling XXXX')

def sub(sig, value):
    if len(value)>65535: return b'XXXX\x04\x00'+struct.pack('<I',len(value))+sig.encode()+b'\0\0'+value
    return struct.pack('<4sH',sig.encode(),len(value))+value

@dataclass
class Record:
    sig: str
    key: str
    source: str
    flags: int
    masters: list[str]
    ss: list[tuple[str,bytes]]
    localized: bool
    @property
    def d(self): return dict(self.ss)
    @property
    def edid(self): return text(self.d.get('EDID',b''))
    @property
    def name(self): return text(self.d.get('FULL',b'')) if not self.localized else ''
    def ref(self, fid):
        if not fid: return None
        index=fid>>24
        if index>len(self.masters): raise ValueError(f'Bad reference {self.source}:{fid:08X}')
        return identity(self.masters[index] if index<len(self.masters) else self.source,fid)
    def refs(self, field): return [self.ref(u32(v)) for k,v in self.ss if k==field and len(v)==4]
    @property
    def keywords(self):
        data=self.d.get('KWDA',b'')
        return [self.ref(u32(data,i)) for i in range(0,len(data),4)]

def read_plugin(path, wanted=None):
    result=[]
    with path.open('rb') as stream, mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as data:
        if data[:4]!=b'TES4': raise ValueError(f'Not TES4: {path}')
        hsize,hflags=struct.unpack_from('<II',data,4)
        header=list(subs(data[24:24+hsize]))
        masters=[text(v) for k,v in header if k=='MAST']
        def walk(start,end):
            p=start
            while p<end:
                sig,n=struct.unpack_from('<4sI',data,p)
                if sig==b'GRUP':
                    label,kind=struct.unpack_from('<4si',data,p+8)
                    if n<24 or p+n>end: raise ValueError(f'Bad group {path}:{p}')
                    if kind!=0 or wanted is None or label.decode('ascii') in wanted: walk(p+24,p+n)
                    p+=n; continue
                if p+24+n>end: raise ValueError(f'Record overflow {path}:{p}')
                typ=sig.decode('ascii')
                if wanted is None or typ in wanted:
                    flags,fid=struct.unpack_from('<II',data,p+8)
                    raw=data[p+24:p+24+n]
                    if flags&0x40000:
                        size=u32(raw); raw=zlib.decompress(raw[4:])
                        if len(raw)!=size: raise ValueError('decompressed size mismatch')
                    ix=fid>>24
                    if ix>len(masters): raise ValueError(f'Bad FormID {path}:{fid:08X}')
                    key=identity(masters[ix] if ix<len(masters) else path.name,fid)
                    result.append(Record(typ,key,path.name,flags,masters,list(subs(raw)),bool(hflags&0x80)))
                p+=24+n
            if p!=end: raise ValueError('group alignment')
        walk(24+hsize,len(data))
        digest=hashlib.sha256(data).hexdigest()
    return result, {'path':str(path),'sha256':digest,'masters':masters,'flags':hflags}

def effective(types=None, progress=False):
    order,paths,roots=environment(); records={}; inputs={}
    for ix,name in enumerate(order):
        rr,meta=read_plugin(paths[name.casefold()],types)
        if rr:
            inputs[name]=meta
            for r in rr:
                if r.flags&0x20: records.pop(r.key,None)
                else: records[r.key]=r
        if progress and ix%400==0: print(f'Parsed {ix}/{len(order)}',flush=True)
    return records,inputs,order,roots

if __name__=='__main__':
    from collections import Counter
    rr,inputs,order,roots=effective({'SPEL','MGEF','BOOK','PERK','FLST','GLOB','KYWD'},True)
    dump(WORK/'build/source-manifest.json',inputs)
    print(Counter(r.sig for r in rr.values()))
    for r in rr.values():
        if r.key.startswith('phenderix elements.esp|') and (r.sig in ('PERK','GLOB') or r.edid.startswith('ZZNovice')):
            print(r.sig,r.key,r.edid,[(k,v.hex()) for k,v in r.ss if k not in ('EDID','FULL','DESC')])
