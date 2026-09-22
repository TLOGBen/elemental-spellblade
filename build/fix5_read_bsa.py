from pathlib import Path
import struct,json

def lz4_frame(raw):
    assert raw[:4] == b'\x04\x22\x4d\x18'
    flags=raw[4];pos=6
    if flags & 8:pos+=8
    if flags & 1:pos+=4
    pos+=1;out=bytearray()
    while True:
        size=struct.unpack_from('<I',raw,pos)[0];pos+=4
        if not size:break
        block=raw[pos:pos+(size&0x7fffffff)];pos+=size&0x7fffffff
        if size&0x80000000:out.extend(block)
        else:
            i=0
            while i<len(block):
                token=block[i];i+=1;n=token>>4
                if n==15:
                    while True:
                        x=block[i];i+=1;n+=x
                        if x!=255:break
                out.extend(block[i:i+n]);i+=n
                if i==len(block):break
                offset=block[i]|block[i+1]<<8;i+=2;n=(token&15)+4
                if (token&15)==15:
                    while True:
                        x=block[i];i+=1;n+=x
                        if x!=255:break
                for _ in range(n):out.append(out[-offset])
        if flags&16:pos+=4
    return bytes(out)

def members(path):
    data=path.read_bytes();magic,ver,offset,flags,nfolders,nfiles,_,_,_=struct.unpack_from('<4s8I',data)
    assert magic==b'BSA\0'
    pos=offset;counts=[]
    for _ in range(nfolders):counts.append(struct.unpack_from('<I',data,pos+8)[0]);pos+=24 if ver==105 else 16
    entries=[]
    for count in counts:
        n=data[pos];pos+=1;folder=data[pos:pos+n].rstrip(b'\0').decode();pos+=n
        for _ in range(count):
            _,size,start=struct.unpack_from('<QII',data,pos);pos+=16;entries.append((folder,size,start))
    for folder,size,start in entries:
        end=data.index(b'\0',pos);name=data[pos:end].decode();pos=end+1
        if not name.lower().endswith('.pex'):continue
        raw=data[start:start+(size&0x3fffffff)]
        if flags&0x100:raw=raw[1+raw[0]:]
        if bool(flags&4)^bool(size&0x40000000):
            expected=struct.unpack_from('<I',raw)[0];raw=lz4_frame(raw[4:]);assert len(raw)==expected
        yield name,raw

class Pex:
    def __init__(self,data):self.b=data;self.p=0;self.strings=[]
    def get(self,fmt):
        v=struct.unpack_from('>'+fmt,self.b,self.p);self.p+=struct.calcsize('>'+fmt);return v[0] if len(v)==1 else v
    def string(self):
        n=self.get('H');s=self.b[self.p:self.p+n].decode();self.p+=n;return s
    def sid(self):return self.strings[self.get('H')]
    def value(self):
        t=self.get('B')
        if t==0:return None
        if t in (1,2):return self.sid()
        if t==3:return self.get('i')
        if t==4:return self.get('f')
        if t==5:return bool(self.get('B'))
        raise ValueError(t)
    def function(self):
        f={'return':self.sid(),'doc':self.sid(),'userFlags':self.get('I'),'flags':self.get('B')}
        f['params']=[(self.sid(),self.sid()) for _ in range(self.get('H'))]
        f['locals']=[(self.sid(),self.sid()) for _ in range(self.get('H'))]
        # Skyrim VM opcode operand counts, with variadic call args at 23..25.
        counts=[0,3,3,3,3,3,3,3,3,3,3,2,2,2,2,2,3,3,3,3,3,1,2,2,3,3,2,1,3,3,3,2,2,3,3,4,4]
        # op 23=jmpf, 24=callmethod,25=callparent,26=callstatic,27=return
        counts=[0]+[3]*9+[2]*5+[3]*5+[1,2,2,3,2,3,1,3,3,3,2,2,3,3,4,4]
        instructions=[]
        for _ in range(self.get('H')):
            op=self.get('B');args=[self.value() for _ in range(counts[op])]
            if op in (23,24,25):args += [[self.value() for _ in range(self.value())]]
            instructions.append((op,args))
        f['code']=instructions;return f
    def read(self):
        assert self.get('I')==0xfa57c0de
        major,minor,game=self.get('BBH');self.get('Q')
        metadata=[self.string() for _ in range(3)]
        self.strings=[self.string() for _ in range(self.get('H'))]
        if self.get('B'):
            self.get('Q')
            for _ in range(self.get('H')):
                self.get('HHHB')
                for _ in range(self.get('H')):self.get('H')
        user=[(self.sid(),self.get('B')) for _ in range(self.get('H'))]
        objects=[]
        for _ in range(self.get('H')):
            o={'name':self.sid(),'size':self.get('I'),'parent':self.sid(),'doc':self.sid(),'flags':self.get('I'),'autoState':self.sid()}
            o['vars']=[(self.sid(),self.sid(),self.get('I'),self.value()) for _ in range(self.get('H'))]
            props=[]
            for _ in range(self.get('H')):
                p={'name':self.sid(),'type':self.sid(),'doc':self.sid(),'flags':self.get('I'),'kind':self.get('B')}
                if p['kind']&4:p['autoVar']=self.sid()
                else:
                    if p['kind']&1:p['get']=self.function()
                    if p['kind']&2:p['set']=self.function()
                props.append(p)
            o['properties']=props;states={}
            for _ in range(self.get('H')):
                state=self.sid();functions={}
                for _ in range(self.get('H')):
                    name=self.sid();functions[name]=self.function()
                states[state]=functions
            o['states']=states;objects.append(o)
        assert self.p==len(self.b),(self.p,len(self.b))
        return {'metadata':metadata,'objects':objects}

if __name__=='__main__':
    mods=Path('D:/Game/Other/SKSE/MO2/mods');out=Path('build/fix5-reference');out.mkdir(exist_ok=True)
    for archive in [mods/'必须模组-MCM Helper-MCM助手/MCMHelper.bsa',mods/'必须模组-SkyUI-界面/SkyUI_SE.bsa']:
        for name,data in members(archive):
            if name.lower() in ('mcm_configbase.pex','ski_configbase.pex','ski_configmanager.pex'):
                (out/name).write_bytes(data)
                parsed=Pex(data).read();(out/(name+'.json')).write_text(json.dumps(parsed,ensure_ascii=False,indent=2),encoding='utf-8')
                o=parsed['objects'][0];print(name,o['parent'],'properties',[(p['name'],p['type']) for p in o['properties']])
                for state,funcs in o['states'].items():
                    for name,f in funcs.items():
                        if name in ('OnConfigInit','OnConfigManagerReady','ShowMessage','LoadConfig','ForcePageReset','OnPageReset','OnInit'):
                            print(state,name,f)
