from pathlib import Path
exec(Path('build/fix18_edit_source.py').read_text(encoding='utf-8-sig').split("c=read('src/ESSBController.psc')")[0])
p='build/papyrus_harness.py';s=read(p).replace("'Actor', 'Actor[]'", "'Actor', 'ActorBase', 'Actor[]'");write(p,s)
p='build/fix18_extra_checks.py';s=read(p).replace("f.v.IsInFaction=lambda x:True", "f.v.IsInFaction=lambda x:True\n            f.c.fields['NecroFaction']=object()");write(p,s)
p='build_v03.py';s=read(p).replace("{e for e,v in manifest.items() if 0x5200 <= int(v['id'],16) < 0x5300}","hit18.new_edids(sys.modules[__name__])").replace("and not 0x5200 <= int(v['id'],16) < 0x5300", "and e not in hit18.new_edids(sys.modules[__name__])").replace("refs resolved (38 GLOB + 4 QUST)","refs resolved (52 GLOB + 5 QUST)").replace('11 aura + 11 persistent marks + 3 status visuals','11 aura removed + 33 weapon-glow tiers + 11 persistent marks + 3 status visuals');write(p,s)
