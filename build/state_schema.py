"""Persisted Papyrus layout gate and the only permitted FormID migration.
No network, game writes, or automatic same-version lock refresh.
"""
from pathlib import Path
import hashlib, json, re
ROOT = Path(__file__).resolve().parents[1]
QUESTS = ('ESSB_MainQuest', 'ESSB_MCMQuest')
LEGACY = dict(zip(QUESTS, (0x800, 0x515B)))

def quest_ids(version):
    if type(version) is not int or not 1 <= version <= 2049:
        raise ValueError('state_schema_version must be an integer in 1..2049')
    return LEGACY.copy() if version == 1 else dict(zip(QUESTS, (0x6000 + (version-2)*2, 0x6001 + (version-2)*2)))

def stub_ids(version):
    return {f'{name}_Schema{v}_Stub': fid for v in range(1, version) for name, fid in quest_ids(v).items()}

def signature(source):
    # Remove comments and whole function/event bodies, so locals never masquerade as members.
    source = re.sub(r';/.*?/;', '', source, flags=re.S)
    source = re.sub(r'\{.*?\}', '', source, flags=re.S)
    source = re.sub(r';[^\n]*', '', source)
    header = re.search(r'(?im)^\s*Scriptname\s+(\w+)\s+extends\s+(\w+)', source)
    if not header: return None
    source = re.sub(r'(?im)^\s*(?:\w+(?:\[\])?\s+)?(?:Function|Event)\s+\w+\([\s\S]*?^\s*End(?:Function|Event)\b', '', source)
    fields = []
    for line in source.splitlines():
        line = line.strip()
        if not line or re.match(r'(?i)(Scriptname|EndProperty|State|EndState|Auto State)\b', line): continue
        m = re.fullmatch(r'(\w+(?:\[\])?)\s+(?:(Property)\s+)?(\w+)(?:\s*=\s*.*?)?(?:\s+(AutoReadOnly|Auto)(?:\s+.*)?)?', line, re.I)
        if not m: raise AssertionError(f'unparsed persisted declaration: {header[1]}: {line}')
        typ, prop, name, storage = m.groups()
        fields.append((name.lower(), typ.lower(), (storage or ('manual-property' if prop else 'member')).lower()))
    return dict(parent=header[2].lower(), members=sorted(fields))

def signatures():
    # Every compiled local script with an instance, plus the inherited MCM member layouts.
    import build_v03 as b
    result = {}
    for name in b.SCRIPTS:
        data = signature((ROOT/'src'/f'{name}.psc').read_text(encoding='utf-8-sig'))
        if data is not None: result[name] = data
    for name in ('MCM_ConfigBase','SKI_ConfigBase','SKI_QuestBase'):
        data = signature((ROOT/'vendor/imports'/f'{name}.psc').read_text(encoding='utf-8-sig'))
        if data is not None: result[name] = data
    return result

def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def check_lock(version, current, lock):
    previous = lock['state_schema_version']
    if version < previous: raise AssertionError('SCHEMA downgrade forbidden: a released quest ID cannot be reused')
    if version == previous and digest(current) != lock['signature_sha256']:
        raise AssertionError('SCHEMA member signature changed without state_schema_version bump; do not edit the lock hash')
    if version > previous and version != previous + 1:
        raise AssertionError('SCHEMA bump must be exactly +1; retain every retired version')
    assert digest(lock['signatures']) == lock['signature_sha256'], 'SCHEMA lock is corrupt'
    assert lock['quests'] == {k:f'{v:06X}' for k,v in quest_ids(previous).items()}, 'SCHEMA quest allocation changed'
    return version > previous

def preflight():
    version = json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']
    quest_ids(version)
    path = ROOT/'state-schema.lock.json'
    assert path.exists(), 'SCHEMA lock missing; restore tracked state-schema.lock.json'
    lock = json.loads(path.read_text(encoding='utf8'))
    current = signatures()
    bumped = check_lock(version, current, lock)
    if bumped:
        history = lock.get('history', []) + [dict(state_schema_version=lock['state_schema_version'], signature_sha256=lock['signature_sha256'], quests=lock['quests'])]
        lock = dict(state_schema_version=version, signature_sha256=digest(current), signatures=current,
                    quests={k:f'{v:06X}' for k,v in quest_ids(version).items()}, history=history)
        raw=path.read_bytes();nl='\r\n' if b'\r\n' in raw else '\n'
        path.write_bytes((json.dumps(lock, ensure_ascii=False, indent=2)+'\n').replace('\n',nl).encode('utf8'))
    return lock

def stable_identity(name, current, old):
    if name not in QUESTS: return current == old
    version = json.loads((ROOT/'settings.json').read_text(encoding='utf8'))['state_schema_version']
    expected = dict(old, id=f'{quest_ids(version)[name]:06X}', formid=f'{0x01000000|quest_ids(version)[name]:08X}')
    # Validate every metadata field as well as the deterministic new ID.
    return current == expected

def verify(records, manifest, builder):
    b=builder; version=b.STATE_SCHEMA_VERSION; by={r.edid:r for r in records}
    previous=json.loads((ROOT/'.codex/pre-fix9-snapshot/v03-formids.json').read_text(encoding='utf8'))['records']
    changed={k:dict(before=v,after=manifest.get(k)) for k,v in previous.items() if manifest.get(k)!=v}
    assert set(changed)==set(QUESTS), changed
    assert all(stable_identity(k,manifest.get(k),v) for k,v in previous.items()), 'non-quest identity drift'
    added={k:v for k,v in manifest.items() if k not in previous}
    assert set(added)==set(stub_ids(version)) | b.GUARD_WINDOW_EDIDS | b.hit18.new_edids(b) | b.hit19.NEW_EDIDS
    for name,fid in stub_ids(version).items():
        r=by[name];assert r.sig=='QUST' and int(r.key.split('|')[1],16)==fid
        assert set(r.d)=={'EDID','FULL','DNAM','NEXT'}, (name,set(r.d))
        assert int.from_bytes(r.d['DNAM'][:2],'little')==0
    assert (b.OUT/'SEQ/Elements Spellblade.seq').read_bytes()==b.I(b.own(b.ID_QUEST))+b.I(b.own(b.ID_MCM_QUEST))
    # Parse VMAD (including alias fragments) rather than searching ambiguous raw byte substrings.
    refs=[]; attached=set(); bindings={}
    def parse_vmad(data):
        import struct
        pos=0
        def unpack(fmt):
            nonlocal pos
            v=struct.unpack_from(fmt,data,pos);pos+=struct.calcsize(fmt);return v
        def string():
            nonlocal pos
            n=unpack('<H')[0];v=data[pos:pos+n].decode('utf8');pos+=n;return v
        def obj():
            unused,alias,fid=unpack('<HHI');refs.append(fid);return fid
        def value(typ):
            nonlocal pos
            if typ==1:obj()
            elif typ==2:string()
            elif typ in (3,4):pos+=4
            elif typ==5:pos+=1
            elif typ in (11,12,13,14,15):
                n=unpack('<I')[0]
                for _ in range(n):value(typ-10)
            else:raise AssertionError(('VMAD type',typ))
        def scripts():
            version,fmt,count=unpack('<HHH');assert version==5 and fmt==2
            for _ in range(count):
                script_name=string();attached.add(script_name);status,n=unpack('<BH')
                props=bindings.setdefault(script_name,{})
                for _ in range(n):
                    name=string();typ,status=unpack('<BB');start=len(refs);value(typ)
                    props[name]=(typ,refs[start:])
        scripts()
        if pos<len(data):
            assert unpack('<B')[0]==2
            assert unpack('<H')[0]==0;assert string()==''
            count=unpack('<H')[0]
            for _ in range(count):obj();scripts()
        assert pos==len(data),(pos,len(data))
    for r in records:
        if 'VMAD' in r.d:parse_vmad(r.d['VMAD'])
    retired={b.own(fid) for fid in stub_ids(version).values()}
    assert not retired.intersection(refs), 'stale VMAD quest reference'
    assert {b.own(b.ID_QUEST), b.own(b.ID_MCM_QUEST)}.issubset(refs)
    # Every fail-closed startup requirement must actually be wired in the generated VMAD.
    source=(ROOT/'src/ESSBController.psc').read_text(encoding='utf8')
    validation=re.search(r'Bool Function ValidateBindings\(\)[\s\S]*?EndFunction',source)[0]
    required=re.findall(r'(?m)^\tIf !(\w+)$',validation)
    for name in required:
        assert name in bindings['ESSBController'], ('missing required Controller VMAD',name)
        typ,targets=bindings['ESSBController'][name]
        if typ in (1,11):assert targets and all(targets), ('empty required binding',name)
    for name in ('LvlGlobals','RatioGlobals','PtsGlobals','ColorGlobals','ShowLvlGlobals','RespecGlobals'):
        typ,targets=bindings['ESSBTrees'][name];assert typ==11 and len(targets)==13 and all(targets),name
    lock=preflight()
    assert {x for x in attached if x.startswith('ESSB')} <= set(lock['signatures'])
    report=dict(version=version,changed=changed,added=added,signature_sha256=lock['signature_sha256'],attached=sorted(attached),vmad_object_refs=len(refs),runtime_tested=False)
    (ROOT/'build/fix9-schema-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'SCHEMA ok: version={version}; 2 fresh quests; {len(stub_ids(version))} inert stubs; {len(b.GUARD_WINDOW_EDIDS)} native window records; member signature locked; all VMAD/SEQ references current; non-quest IDs unchanged')
    return report
