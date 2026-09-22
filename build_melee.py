"""Current scope: build only melee damage and its independent settings power."""
import json,subprocess,hashlib
from tes import ROOT,WORK,dump
from build_core import main as build_core,OUT

def main():
    build_core()
    psc=OUT/'Source/Scripts';pex=OUT/'Scripts'
    psc.mkdir(parents=True,exist_ok=True);pex.mkdir(exist_ok=True)
    names=['ESSBPlayerAlias','ESSBSettingsEffect']
    for folder,extension in [(psc,'.psc'),(pex,'.pex')]:
        unexpected=[p.name for p in folder.iterdir() if p.name not in {n+extension for n in names}]
        if unexpected:raise ValueError(f'Unexpected deployment scripts: {unexpected}')
    compiler=ROOT/'MO2/mods/动作共存-Nemesis Unlimited Behavior Engine-动作刷新/Nemesis_Engine/Papyrus Compiler/PapyrusCompiler.exe'
    imports=';'.join(str(p) for p in [WORK/'vendor/compiler-api',WORK/'vendor/imports',psc])
    results=[]
    for name in names:
        source=psc/(name+'.psc')
        source.write_text((WORK/'src'/(name+'.psc')).read_text(encoding='utf-8'),encoding='utf-8-sig')
        command=[str(compiler),str(source),'-i='+imports,'-o='+str(pex),'-f='+str(WORK/'vendor/imports/TESV_Papyrus_Flags.flg'),'-optimize']
        run=subprocess.run(command,cwd=WORK/'build',capture_output=True,text=True,encoding='utf-8',errors='replace')
        results.append({'script':name,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
        print(name,'OK' if run.returncode==0 else 'FAILED')
        if run.returncode:print(run.stdout,run.stderr)
    dump(WORK/'build/melee-compiler-results.json',results)
    if any(r['exit_code'] for r in results):raise SystemExit(1)
    dump(WORK/'build/package-hashes.json',{str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob('*')) if p.is_file()})

if __name__=='__main__':main()
