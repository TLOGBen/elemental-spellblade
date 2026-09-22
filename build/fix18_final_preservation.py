from pathlib import Path
import hashlib,json,re
root=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((root/'build/fix18-third-start-preservation.json').read_text(encoding='utf8'))
for name,digest in p['snapshot'].items():assert sha(root/name)==digest,name
pre=root/'build/fix18-zero-difference-preflight.json';assert sha(pre)==p['preflight']
log=(root/'build/fix18-build-final.log').read_text(encoding='utf8')
for token in ['READBACK ok:',"masters=['Skyrim.esm']",'records=4067 manifest=4067','CSF ok: files=13 valid=13','DELIVERY ok:','LAYOUT ok:','DOT ok:','MCM ok:','MCM DEFAULTS ok:','SCHEMA ok: version=7','HITPROC ok:','FIX17 ok:','FIX18 ok:','unmapped=0']:
 assert token in log,token
for i in range(10,17):assert re.search(r'FIX'+str(i)+r'.* ok:',log),i
assert len(re.findall(r'^  compile .*: OK$',log,re.M))==20
formats={}
for path in [root/'build_v03.py',*sorted((root/'src').glob('*.psc'))]:
 raw=path.read_bytes();raw.decode('utf-8-sig');old=root/'.codex/pre-fix18-snapshot'/('src/'+path.name if path.suffix=='.psc' else path.name)
 if old.exists():
  prior=old.read_bytes();assert raw.startswith(b'\xef\xbb\xbf')==prior.startswith(b'\xef\xbb\xbf'),path.name
  if b'\r\n' in prior:assert b'\n' not in raw.replace(b'\r\n',b''),path.name
 formats[path.name]={'bom':raw.startswith(b'\xef\xbb\xbf'),'crlf':raw.count(b'\r\n'),'bare_lf':raw.replace(b'\r\n',b'').count(b'\n')}
assert formats['build_v03.py']['bare_lf']==0
status=['ESSBStatus','ESSBMark','ESSBElem','ESSBElem2','ESSBElem3','ESSBReactions']
for name in status:assert (root/'src'/f'{name}.psc').read_bytes()==(root/'.codex/pre-fix18-snapshot/src'/f'{name}.psc').read_bytes()
package=root/'package/Elements Spellblade';artifacts=[package/'Elements Spellblade.esp',*sorted((package/'Scripts').glob('*.pex'))]
assert len(artifacts)==21,len(artifacts)
report=dict(build_exit_code=0,build_log='build/fix18-build-final.log',compiled_scripts=20,snapshot_files_preserved=len(p['snapshot']),preflight_preserved=True,status_sources_byte_identical=status,encodings=formats,artifacts={str(x.relative_to(root)):sha(x) for x in artifacts},runtime_tested=False,deployed=False)
(root/'build/fix18-final-preservation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('PRESERVATION ok: 24 snapshot files + preflight unchanged; 6 status sources unchanged; encodings/CRLF retained; 20 PEX + ESP hashed')
