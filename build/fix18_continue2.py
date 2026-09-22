from pathlib import Path
exec(Path('build/fix18_edit_source.py').read_text(encoding='utf-8-sig').split("c=read('src/ESSBController.psc')")[0])
p='build/fix13_verify.py';s=read(p).replace("refs=s.refs('EFID');assert len(refs)==2 and refs[1]==drain.key", "refs=s.refs('EFID');assert len(refs)==3 and refs[1]==drain.key and refs[2]==by['ESSB_EngagedEffect'].key").replace('lightning_effects=2','lightning_effects=3');write(p,s)
p='build/fix18_engine_evidence.py';s=read(p).replace('if interesting and (ep or len(rows)<20):','if interesting:');write(p,s)
p='src/ESSBController.psc';s=read(p);s=s.replace('TickDomain()\n\tRefreshSyncStage()\n\tIf procDirty', 'TickDomain()\n\tRefreshSyncStage()\n\tIf oldStage != CachedSyncStage\n\t\tPushSyncStage()\n\t\tRefreshDivineProtection()\n\tEndIf\n\tIf procDirty');write(p,s)
