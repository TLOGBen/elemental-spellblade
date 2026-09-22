"""Stage compiler imports only; never install vanilla scripts into the game."""
import hashlib, struct, zipfile, zlib, sys
from pathlib import Path
from tes import WORK, ROOT, dump
sys.path.insert(0,str(ROOT/'.codex/localization/vendor'))

def bsa_members(path):
    data=path.read_bytes()
    magic,version,offset,flags,nfolders,nfiles,folderlen,filelen,fileflags=struct.unpack_from('<4s8I',data)
    assert magic==b'BSA\0' and version in (104,105), (magic,version)
    pos=offset; counts=[]
    for _ in range(nfolders):
        counts.append(struct.unpack_from('<I',data,pos+8)[0]); pos+=24 if version==105 else 16
    entries=[]
    for count in counts:
        length=data[pos]; pos+=1
        folder=data[pos:pos+length].rstrip(b'\0').decode(); pos+=length
        for _ in range(count):
            _,size,start=struct.unpack_from('<QII',data,pos); pos+=16
            entries.append((folder,size,start))
    for folder,size,start in entries:
        end=data.index(b'\0',pos); name=data[pos:end].decode(); pos=end+1
        member=(folder+'/'+name).replace('\\','/')
        if not member.lower().endswith('.psc'): continue
        raw=data[start:start+(size&0x3FFFFFFF)]
        if flags&0x100: raw=raw[1+raw[0]:]
        if bool(flags&4)^bool(size&0x40000000):
            expected=struct.unpack_from('<I',raw)[0]
            if version==105:
                import lz4.frame
                raw=lz4.frame.decompress(raw[4:])
            else: raw=zlib.decompress(raw[4:])
            assert len(raw)==expected
        yield member,raw

def main():
    dest=WORK/'vendor/imports'; dest.mkdir(exist_ok=True)
    manifest={}
    with zipfile.ZipFile(WORK/'vendor/skse64.zip') as z:
        names={n.split('/scripts/',1)[1]:n for n in z.namelist() if '/scripts/' in n and not n.endswith('/')}
        basenames={n.split('/')[-1] for n in names if n.startswith(('vanilla/','modified/')) and n.endswith(('.psc','.flg'))}
        for name in basenames:
            parts=[z.read(names[p+'/'+name]) for p in ('vanilla','modified') if p+'/'+name in names]
            raw=b'\n\n'.join(parts)
            (dest/name).write_bytes(raw)
            manifest[name]={'provider':'ianpatt/skse64','sha256':hashlib.sha256(raw).hexdigest()}
    bsa=ROOT/'MO2/mods/必须模组-UIExtensions-状态栏扩展/UIExtensions.bsa'
    for member,raw in bsa_members(bsa):
        name=member.split('/')[-1]; (dest/name).write_bytes(raw)
        manifest[name]={'provider':str(bsa),'member':member,'sha256':hashlib.sha256(raw).hexdigest()}
    for name,path in {
        'Debug.psc':ROOT/'MO2/mods/动作共存-Nemesis Unlimited Behavior Engine-动作刷新/Nemesis_Engine/Papyrus Compiler/scripts/Debug.psc',
        'UILIB_1.psc':ROOT/'MO2/mods/Simple Obvious Spell-Crafting 2/Source/Scripts/UILIB_1.psc',
        'PO3_Events_Alias.psc':ROOT/"MO2/mods/powerofthree's Papyrus Extender/Source/scripts/PO3_Events_Alias.psc",
    }.items():
        raw=path.read_bytes();(dest/name).write_bytes(raw)
        manifest[name]={'provider':str(path),'sha256':hashlib.sha256(raw).hexdigest()}
    dump(WORK/'vendor/compiler-sources.json',manifest)
    print('Compiler import files:',len(manifest))
    print('UIExtensions sources:',[n for n in manifest if n.lower().startswith('ui')])

if __name__=='__main__': main()
