"""Generate isolated, opt-in native engine probes. Never deployed automatically."""
from pathlib import Path
import collections,struct,json,subprocess,shutil,runpy

def run(b):
    folder=b.WORK/'build/fix18-probe-package';folder.mkdir(exist_ok=True)
    rows=[]
    def add(sig,fid,edid,ss):rows.append((sig,b.record(sig,b.own(fid),[('EDID',b.Z(edid))]+ss)))
    add('KYWD',0x800,'ESSB_Probe',[('CNAM',bytes(4))])
    for fid, segment in [(0x801,1),(0x802,2),(0x803,3),(0x804,4)]:
        keyword = [('KSIZ',b.I(1)),('KWDA',b.I(b.own(0x800)))] if segment != 4 else []
        add('MGEF',fid,'ESSB_ProbeEffect'+str(segment),[('VMAD',b.vmad('ESSBProbeSegment',{'Segment':(3,segment)})),('FULL',b.Z('Round 18 probe fire damage'))]+keyword+[('DATA',b.mgef_data(b.MGEF_HIT_FLAGS,0,base_cost=1,skill=20,resist=41,actor_value=24,casting=1,delivery=1,skill_usage=0))])
    for fid,name,damage,effect in [(0x810,'ESSB_ProbeA',5,0x801),(0x811,'ESSB_ProbeB',7,0x802),(0x812,'ESSB_ProbeMagnitude',10,0x803),(0x813,'ESSB_ProbeReference',10,0x804)]:
        keyword = [('KSIZ',b.I(1)),('KWDA',b.I(b.own(0x800)))] if fid != 0x813 else []
        add('SPEL',fid,name,[('FULL',b.Z(name))]+keyword+[('SPIT',b.spit(0,1,1)),('EFID',b.I(b.own(effect))),('EFIT',struct.pack('<fII',damage,0,0))])
    for fid,name in [(0x832,'ESSB_ProbeGate'),(0x833,'ESSB_ProbeSession'),(2160, 'TieVariant'), (2161, 'TieResult1'), (2162, 'TieResult2'), (2163, 'TieResult3'), (2164, 'TieResult4')]:
        add('GLOB',fid,name,[('FNAM',b'f'),('FLTV',b.F(0.0))])
    props={name:(1,b.own(fid)) for name,fid in [('ProbeAB',0x820),('ProbeHit',0x821),('ProbeMultiply',0x822),('Gate',0x832),('Session',0x833),('ReferenceSpell',0x813),('CrossA',0x850),('CrossB',0x851),('CrossA2',0x852),('CrossB2',0x853),('TieA', 2144), ('TieB', 2145), ('TieA2', 2147), ('TieB2', 2146), ('TieVariant', 2160), ('TieResult1', 2161), ('TieResult2', 2162), ('TieResult3', 2163), ('TieResult4', 2164)]}
    add('MGEF',0x830,'ESSB_ProbeMeterEffect',[('VMAD',b.vmad('ESSBProbeMeter',props)),('FULL',b.Z('Round 18 manual meter')),('DATA',b.mgef_data(0x8800,1,casting=0,delivery=0))])
    # Meter attaches directly to the owned bandit (console appendix retained). CTDA runs on Reference=Player (0x14), OR AB/Hit.
    add('SPEL',0x831,'ESSB_ProbeMeter',[('FULL',b.Z('ESSB Probe Meter')),('SPIT',b.spit(1,0,0)),('EFID',b.I(b.own(0x830))),('EFIT',struct.pack('<fII',0,0,0)),('CTDA',b.ctda(1,1,448,b.own(0x820),run_on=2,reference=0x14)),('CTDA',b.ctda(1,1,448,b.own(0x821),run_on=2,reference=0x14)),('CTDA',b.ctda(1,1,448,b.own(0x850),run_on=2,reference=0x14)),('CTDA',b.ctda(1,1,448,b.own(0x852),run_on=2,reference=0x14)),('CTDA',b.ctda(1,1,448,b.own(0x860),run_on=2,reference=0x14)),('CTDA',b.ctda(0,1,448,b.own(0x863),run_on=2,reference=0x14))])
    # Native entry 51, priority and spell 5/7/10 unchanged. Gate permits a real
    # physical-only control hit; meter-target condition excludes unarmed actors.
    conditions=[(2,b.ctda(0,0,f)) for f in (453,700,46,569)]
    conditions += [(0,b.ctda(0,1,74,b.own(0x832))),(2,b.ctda(0,1,214,b.own(0x830)))]
    conditions.sort(key=lambda row:row[0])
    both=[]
    for priority,fid in [(200,0x810),(199,0x811)]:
        fragment=b.entry(51,b.own(fid),conditions,function=10,epft=5)
        fragment[0]=('PRKE',bytes([2,0,priority]));both+=fragment
    add('PERK',0x820,'ESSB_ProbeAB',[('FULL',b.Z('Probe 5 + 7')),('DATA',b.perk_data(playable=0,hidden=1))]+both)
    add('PERK',0x821,'ESSB_ProbeMagnitudeHit',[('FULL',b.Z('Probe 10')),('DATA',b.perk_data(playable=0,hidden=1))]+b.entry(51,b.own(0x812),conditions,function=10,epft=5))
    add('PERK',0x822,'ESSB_ProbeMultiply',[('FULL',b.Z('Probe keyword x2')),('DATA',b.perk_data(playable=0,hidden=1))]+b.entry(29,2.0,[(1,b.ctda(0,1,560,b.own(0x800)))]))
    # Separate single-entry perks: ranks equal; priority vs FormID/add order crossed.
    for fid,name,spell,priority in [(0x850,'ESSB_ProbeCrossA',0x810,200),(0x851,'ESSB_ProbeCrossB',0x811,199),(0x852,'ESSB_ProbeCrossA2',0x810,199),(0x853,'ESSB_ProbeCrossB2',0x811,200),(0x860,'ESSB_ProbeTieA',0x810,0),(0x861,'ESSB_ProbeTieB',0x811,0),(0x863,'ESSB_ProbeTieA2',0x810,0),(0x862,'ESSB_ProbeTieB2',0x811,0)]:
        fragment=b.entry(51,b.own(spell),conditions,function=10,epft=5)
        fragment[0]=('PRKE',bytes([2,0,priority]))
        add('PERK',fid,name,[('FULL',b.Z(name)),('DATA',b.perk_data(playable=0,hidden=1))]+fragment)
    runpy.run_path(str(b.WORK/'build/fix18e_records.py'))['add_records'](b, add, folder)
    groups=collections.defaultdict(list)
    for sig,raw in rows:groups[sig].append(raw)
    header=[('HEDR',struct.pack('<fII',1.7,len(rows)+len(groups),0x882)),('CNAM',b.Z('Elements Spellblade offline probe')),('MAST',b.Z('Skyrim.esm')),('DATA',bytes(8))]
    body=b.record('TES4',0,header,0)
    for sig,records in groups.items():
        payload=b''.join(records);body+=struct.pack('<4sI4sIHHHH',b'GRUP',24+len(payload),sig.encode(),0,0,0,0,0)+payload
    path=folder/'Elements Spellblade Round18 Probes.esp';path.write_bytes(body)
    rr,meta=b.read_plugin(path);assert len(rr)==40 and meta['masters']==['Skyrim.esm']
    by={r.edid:r for r in rr};assert by['ESSB_ProbeAB'].d['EPFT']==bytes([5])
    # Compile into the opt-in folder only; release SCRIPTS whitelist is untouched.
    compiler=b.ROOT/'MO2/mods/动作共存-Nemesis Unlimited Behavior Engine-动作刷新/Nemesis_Engine/Papyrus Compiler/PapyrusCompiler.exe'
    psc=folder/'Source/Scripts';pex=folder/'Scripts'
    psc.mkdir(parents=True,exist_ok=True);pex.mkdir(exist_ok=True)
    compiles=[]
    for name in ('ESSBProbeMeter','ESSBProbeSegment','ESSBProbeSetup','ESSBProbePower'):
        shutil.copyfile(b.WORK/'src'/f'{name}.psc',psc/f'{name}.psc')
        imports=';'.join(str(p) for p in [b.WORK/'vendor/compiler-api',b.WORK/'vendor/imports',psc])
        result=subprocess.run([str(compiler),str(psc/f'{name}.psc'),'-i='+imports,'-o='+str(pex),'-f='+str(b.WORK/'vendor/imports/TESV_Papyrus_Flags.flg'),'-optimize'],cwd=folder,capture_output=True,text=True,encoding='utf8',errors='replace')
        compiles.append(dict(script=name,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        if result.returncode: raise AssertionError(result.stdout+'\n'+result.stderr)
        assert (pex/f'{name}.pex').is_file()
    report={'plugin':str(path.relative_to(b.WORK)),'masters':meta['masters'],'records':{r.edid:r.key for r in rr},'runtime_tested':False,'activation':'start-game-enabled player alias grants five lesser powers on init/load; setup powers own bandit reference and perks','compiles':compiles}
    (folder/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    runpy.run_path(str(b.WORK/'build/fix18b_verify.py'))['run'](b)
    runpy.run_path(str(b.WORK/'build/fix18c_verify.py'))['run'](b)
    runpy.run_path(str(b.WORK/'build/fix18d_verify.py'))['run'](b)
    runpy.run_path(str(b.WORK/'build/fix18e_verify.py'))['run'](b)
    runpy.run_path(str(b.WORK/'build/fix18f_verify.py'))['run'](b)
    runpy.run_path(str(b.WORK/'build/fix18g_verify.py'))['run'](b)
    print('PROBES ok: isolated opt-in 40 records + 4 compiled scripts + startup SEQ; sole master Skyrim.esm; no deployment / save generated')
    return report
